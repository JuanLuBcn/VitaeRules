"""
Conversational Orchestrator - Main bot personality.

The Orchestrator IS the bot. It:
- Analyzes user messages directly (no separate intent classifier)
- Maintains minimal conversation context (last 2 turns)
- Uses specialized agents as stateless tools
- Generates natural, user-facing responses
- Handles confirmation flow for clarity

Design principles for 1.7B model:
- Short, focused prompts
- Minimal context window
- One task per LLM call
- Template-based questions where possible
"""

from typing import Any
from app.llm import LLMService
from app.memory import MemoryService
from app.tools.list_tool import ListTool
from app.tools.task_tool import TaskTool
from app.crews.retrieval import RetrievalCrew
from app.tracing import get_tracer
from app.utils import extract_media_reference

logger = get_tracer()


class ConversationalOrchestrator:
    """
    The bot's personality. Manages conversation and uses agents as tools.
    """
    
    def __init__(self, llm_service: LLMService, memory_service: MemoryService):
        """Initialize orchestrator with tools."""
        self.llm = llm_service
        self.memory = memory_service
        self.tracer = get_tracer()
        
        # Tools (stateless, no LLM, just DB operations)
        self.list_tool = ListTool()
        self.task_tool = TaskTool()
        # Pass LLM service to RetrievalCrew (needed for CrewAI agents)
        self.retrieval_crew = RetrievalCrew(memory_service=memory_service, llm=llm_service)
        
        # Minimal conversation context (last 2 turns per chat)
        # {chat_id: {action, entities, waiting_for, last_question}}
        self.contexts = {}
    
    async def handle_message(
        self, message: str, chat_id: str, user_id: str
    ) -> dict:
        """
        Main conversation handler.
        
        Returns:
            dict with:
                - message: Response to user
                - waiting_for_input: bool (conversation continues)
        """
        self.tracer.info(
            "message_received", 
            extra={
                "chat_id": chat_id,
                "user_id": user_id,
                "message": message[:100],
                "message_length": len(message)
            }
        )
        
        # Extract media reference if present
        clean_message, media_ref = extract_media_reference(message)
        
        if media_ref:
            self.tracer.info(
                "media_detected",
                extra={
                    "media_type": media_ref.media_type,
                    "has_path": bool(media_ref.media_path)
                }
            )
        
        # Check if we're mid-conversation
        context = self.contexts.get(chat_id)
        
        if context and context.get("waiting_for"):
            # We asked a question, this is the answer
            self.tracer.info(
                "continuing_conversation",
                extra={
                    "chat_id": chat_id,
                    "waiting_for": context.get("waiting_for"),
                    "has_context": True
                }
            )
            return await self._handle_answer(
                clean_message, media_ref, context, chat_id, user_id
            )
        else:
            # New request
            self.tracer.info(
                "new_conversation",
                extra={"chat_id": chat_id, "has_context": False}
            )
            return await self._handle_new_request(
                clean_message, media_ref, chat_id, user_id
            )
    
    async def _handle_new_request(
        self, message: str, media_ref, chat_id: str, user_id: str
    ) -> dict:
        """Analyze new message and decide action."""
        
        self.tracer.info(
            "analyzing_new_request", 
            extra={
                "message": message[:200],
                "has_media": bool(media_ref)
            }
        )
        
        # OPTION A: Let LLM generate natural response + optionally call tool
        analysis = await self._analyze_message(message, media_ref)
        
        reply = analysis.get("reply", "No entendí bien.")
        tool_call = analysis.get("tool_call")
        
        self.tracer.info(
            "llm_analysis_complete",
            extra={
                "reply": reply[:150],
                "has_tool_call": tool_call is not None,
                "tool_name": tool_call.get("name") if tool_call else None,
                "tool_args": list(tool_call.get("args", {}).keys()) if tool_call else None
            }
        )
        
        # If LLM wants to call a tool, execute it
        if tool_call and tool_call.get("name"):
            self.tracer.info(
                "executing_tool_call",
                extra={
                    "tool": tool_call.get("name"),
                    "args": tool_call.get("args", {})
                }
            )
            
            try:
                result = await self._execute_tool_call(
                    tool_call, media_ref, user_id
                )
                
                # Check if it's a chat fallback response
                if result.get("chat_response"):
                    # Memory search was empty, return chat fallback
                    self.tracer.info(
                        "chat_fallback_triggered",
                        extra={
                            "tool": tool_call.get("name"),
                            "fallback_reason": "empty_results"
                        }
                    )
                    self.contexts.pop(chat_id, None)
                    return {
                        "message": result["chat_response"],
                        "waiting_for_input": False
                    }
                
                # Tool executed successfully
                self.tracer.info(
                    "tool_executed_successfully",
                    extra={
                        "tool": tool_call.get("name"),
                        "result_keys": list(result.keys())
                    }
                )
                
                # Clear any pending context
                self.contexts.pop(chat_id, None)
                
                return {
                    "message": reply,  # LLM's natural message
                    "waiting_for_input": False
                }
            
            except Exception as e:
                self.tracer.error(
                    "tool_execution_error",
                    extra={
                        "tool": tool_call.get("name"),
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                )
                return {
                    "message": f"{reply}\n\n(Hubo un error ejecutando: {str(e)})",
                    "waiting_for_input": False
                }
        
        else:
            # LLM is asking a question or needs more info
            self.tracer.info(
                "llm_asking_question",
                extra={
                    "question": reply[:150],
                    "needs_more_info": True
                }
            )
            
            # Save minimal context
            self.contexts[chat_id] = {
                "last_message": message,
                "last_reply": reply,
                "waiting_for_more": True
            }
            
            return {
                "message": reply,
                "waiting_for_input": True
            }
    
    async def _analyze_message(self, message: str, media_ref) -> dict:
        """
        Natural conversation with progressive information gathering.
        
        The LLM:
        - Analyzes what the user wants
        - Asks When/How/Where/With Who based on context
        - After 1-2 questions, has enough to execute
        - Never asks "what do you want to do?" - infers from context
        """
        
        media_context = ""
        if media_ref:
            media_context = f"\n[Archivo adjunto: {media_ref.media_type}]"
        
        prompt = f"""Analiza el significado semántico de este mensaje:

"{message}"{media_context}

Eres un asistente personal. Determina QUÉ QUIERE el usuario según el PROPÓSITO COMUNICATIVO del mensaje.

ACCIONES DISPONIBLES:

1. search_memory
   El usuario está PREGUNTANDO por información que previamente le has guardado.
   Busca RECUPERAR conocimiento personal, eventos pasados, conversaciones anteriores.
   Señales: Preguntas sobre el pasado, "¿qué me dijiste?", "¿dónde guardé?", "¿qué hablamos?"

2. save_note
   El usuario está AFIRMANDO información nueva que quiere que guardes.
   Está INFORMANDO sobre hechos, eventos, características de personas/cosas.
   Señales: Afirmaciones, "María me dijo...", "guarda que...", "anota que..."

3. create_task
   El usuario quiere establecer un RECORDATORIO o compromiso FUTURO.
   Está delegando que le recuerdes algo en un momento específico.
   Señales: "Recuérdame...", "avísame...", acciones futuras con tiempo

4. add_to_list
   El usuario quiere AGREGAR elementos a una colección categorizada.
   Gestiona items agrupados por contexto (compra, trabajo, etc).
   Señales: "Añade a...", "pon en la lista...", items sueltos ("leche", "pan")

5. CHAT (conversación general)
   El usuario busca CONVERSACIÓN, opiniones, consejos, o conocimiento GENERAL.
   Solicita razonamiento, análisis, o información que NO ha almacenado antes.
   Señales: "¿Qué opinas?", "¿Por qué?", "¿Cómo estás?", preguntas filosóficas

REGLAS DE ANÁLISIS SEMÁNTICO:

Pregúntate:
- ¿Está AFIRMANDO algo nuevo para guardar? → save_note
- ¿Está PREGUNTANDO por algo que ÉL/ELLA te contó antes? → search_memory
- ¿Está PREGUNTANDO por opinión/conocimiento general? → CHAT, NO llames tool
- ¿Está pidiendo un RECORDATORIO futuro? → create_task
- ¿Está AÑADIENDO a una colección/lista? → add_to_list

Si FALTA INFORMACIÓN (cuándo, dónde, qué lista):
- NO llames tool_call todavía
- PREGUNTA naturalmente: "¿Cuándo?", "¿A qué lista?", "¿Con quién?"
- Después de 1-2 respuestas, tendrás suficiente info

Si NO ESTÁS SEGURO o es AMBIGUO:
- Responde naturalmente (CHAT mode)
- NO llames tool
- Mejor una conversación que una acción incorrecta

IMPORTANTE: 
- Para search_memory: Solo si pregunta por algo GUARDADO (pasado personal)
- Si search_memory no encuentra nada, yo hago fallback a chat automáticamente
- Para CHAT general: NO llames tool, solo responde naturalmente

RESPONDE en español, natural y conciso.

Formato JSON:
{{
  "reply": "tu respuesta natural al usuario",
  "tool_call": {{"name": "tool_name", "args": {{...}}}} O null si no hay tool
}}"""
        
        system_prompt = """Asistente conversacional en español.
Analiza el propósito semántico del mensaje.
Si falta info: pregunta naturalmente.
Si tienes info completa: ejecuta tool.
Si es conversación: responde sin tool.
JSON válido, sin markdown."""
        
        try:
            self.tracer.info(
                "calling_llm_for_analysis",
                extra={
                    "prompt_length": len(prompt),
                    "has_media": bool(media_ref)
                }
            )
            
            result = self.llm.generate_json(prompt, system_prompt)
            
            self.tracer.info(
                "llm_raw_response",
                extra={
                    "reply": result.get("reply", "")[:150],
                    "tool_call": result.get("tool_call")
                }
            )
            
            # Validate response format
            if "reply" not in result:
                self.tracer.warning("llm_response_missing_reply")
                result["reply"] = "Lo siento, no entendí bien."
            if "tool_call" not in result:
                result["tool_call"] = None
            
            return result
        
        except Exception as e:
            self.tracer.error(
                "llm_analysis_error",
                extra={
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            )
            return {
                "reply": "Perdón, tuve un problema procesando eso. ¿Puedes repetir?",
                "tool_call": None
            }
    
    def _check_missing_fields(self, action_type: str, entities: dict) -> list:
        """Check what essential fields are missing."""
        
        required = {
            "task": ["title"],
            "note": ["content"],
            "list": ["items"],  # list_name optional (can infer)
            "query": ["query"]
        }
        
        missing = []
        for field in required.get(action_type, []):
            if not entities.get(field):
                missing.append(field)
        
        return missing
    
    async def _ask_for_missing(
        self, action_type: str, entities: dict, field: str, chat_id: str
    ) -> dict:
        """Ask naturally for missing info using templates."""
        
        # Template-based questions (no LLM needed - faster!)
        questions = {
            "task": {
                "title": "¿Qué tarea quieres crear?",
                "due_at": "¿Cuándo quieres que te lo recuerde?",
            },
            "note": {
                "content": "¿Qué quieres que guarde?",
            },
            "list": {
                "items": "¿Qué quieres añadir?",
                "list_name": "¿A qué lista lo añado?",
            },
            "query": {
                "query": "¿Qué quieres buscar?",
            }
        }
        
        question = questions.get(action_type, {}).get(
            field, "¿Puedes darme más detalles?"
        )
        
        # Save minimal context
        self.contexts[chat_id] = {
            "action_type": action_type,
            "entities": entities,
            "waiting_for": field,
            "last_question": question
        }
        
        self.tracer.info(
            "asking_for_field",
            extra={"field": field, "action": action_type}
        )
        
        return {"message": question, "waiting_for_input": True}
    
    async def _show_understanding_and_confirm(
        self, action_type: str, entities: dict, chat_id: str, user_id: str
    ) -> dict:
        """
        Show what we understood and ask for confirmation.
        
        This replaces dual LLM verification - user confirms instead.
        """
        
        # Generate preview of what we'll do
        preview = self._generate_preview(action_type, entities)
        
        # Save context for confirmation
        self.contexts[chat_id] = {
            "action_type": action_type,
            "entities": entities,
            "waiting_for": "confirmation",
            "user_id": user_id
        }
        
        confirmation_msg = f"{preview}\n\n¿Correcto? (sí/no)"
        
        return {"message": confirmation_msg, "waiting_for_input": True}
    
    def _generate_preview(self, action_type: str, entities: dict) -> str:
        """Generate user-friendly preview of action."""
        
        if action_type == "task":
            title = entities.get("title", "Sin título")
            due = entities.get("due_at", "")
            preview = f"✅ Crear tarea: **{title}**"
            if due:
                preview += f"\n📅 Cuándo: {due}"
            return preview
        
        elif action_type == "note":
            content = entities.get("content", "")[:100]
            preview = f"💾 Guardar nota: {content}"
            people = entities.get("people", [])
            if people:
                preview += f"\n👤 Personas: {', '.join(people)}"
            return preview
        
        elif action_type == "list":
            items = entities.get("items", [])
            list_name = entities.get("list_name", "tu lista")
            preview = f"📝 Añadir a {list_name}:\n"
            preview += "\n".join(f"  • {item}" for item in items)
            return preview
        
        elif action_type == "query":
            query = entities.get("query", "")
            return f"🔍 Buscar: {query}"
        
        return "Procesando..."
    
    async def _handle_answer(
        self, answer: str, media_ref, context: dict, chat_id: str, user_id: str
    ) -> dict:
        """Process answer in continued conversation."""
        
        # Combine context with new answer for LLM
        last_reply = context.get("last_reply", "")
        combined_context = f"[Antes pregunté: {last_reply}]\nUsuario responde: {answer}"
        
        self.tracer.info(
            "processing_answer",
            extra={
                "answer": answer[:150],
                "previous_question": last_reply[:100],
                "combined_context_length": len(combined_context)
            }
        )
        
        # Let LLM continue the conversation
        analysis = await self._analyze_message(combined_context, media_ref)
        
        reply = analysis.get("reply", "No entendí.")
        tool_call = analysis.get("tool_call")
        
        # If LLM wants to call tool now
        if tool_call and tool_call.get("name"):
            self.tracer.info(
                "answer_triggered_tool",
                extra={
                    "tool": tool_call.get("name"),
                    "conversation_turns": len(context)
                }
            )
            
            try:
                result = await self._execute_tool_call(tool_call, media_ref, user_id)
                
                # Check if it's a chat fallback response
                if result.get("chat_response"):
                    # Memory search was empty, return chat fallback
                    self.tracer.info(
                        "chat_fallback_in_conversation",
                        extra={
                            "tool": tool_call.get("name"),
                            "fallback_reason": "empty_results"
                        }
                    )
                    self.contexts.pop(chat_id, None)
                    return {
                        "message": result["chat_response"],
                        "waiting_for_input": False
                    }
                
                # Clear context - conversation done
                self.tracer.info(
                    "conversation_complete",
                    extra={
                        "tool": tool_call.get("name"),
                        "turns": len(context)
                    }
                )
                self.contexts.pop(chat_id, None)
                
                return {
                    "message": reply,
                    "waiting_for_input": False
                }
            
            except Exception as e:
                self.tracer.error(
                    "tool_error_in_conversation",
                    extra={
                        "tool": tool_call.get("name"),
                        "error": str(e)
                    }
                )
                return {
                    "message": f"{reply}\n\n(Error: {str(e)})",
                    "waiting_for_input": False
                }
        
        else:
            # LLM still needs more info
            self.tracer.info(
                "llm_needs_more_info",
                extra={
                    "question": reply[:150],
                    "turn_count": len(context)
                }
            )
            
            context["last_message"] = answer
            context["last_reply"] = reply
            
            return {
                "message": reply,
                "waiting_for_input": True
            }
    
    async def _execute_tool_call(
        self, tool_call: dict, media_ref, user_id: str
    ) -> dict:
        """Execute the tool that LLM wants to call."""
        
        tool_name = tool_call.get("name")
        args = tool_call.get("args", {})
        
        self.tracer.info(
            "executing_tool",
            extra={"tool": tool_name, "args": list(args.keys())}
        )
        
        # Add media to args if present
        if media_ref:
            args["media_path"] = media_ref.media_path
            args["media_type"] = media_ref.media_type
        
        if tool_name == "create_task":
            return await self._tool_create_task(user_id, args)
        
        elif tool_name == "save_note":
            return await self._tool_save_note(user_id, args)
        
        elif tool_name == "add_to_list":
            return await self._tool_add_to_list(user_id, args)
        
        elif tool_name == "search_memory":
            result = await self._tool_search_memory(user_id, args)
            
            # Check if we need to fallback to chat
            if result.get("fallback_to_chat"):
                # Memory search returned empty - fallback to chat
                query = result.get("query", "")
                
                # Generate chat response with context about empty search
                fallback_response = await self._chat_fallback(
                    query=query,
                    user_id=user_id,
                    context="No memories found, offering to store or providing general help"
                )
                
                return fallback_response
            
            return result
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    async def _tool_create_task(self, user_id: str, args: dict) -> dict:
        """Create task tool."""
        self.tracer.info(
            "creating_task",
            extra={
                "user_id": user_id,
                "title": args.get("title", "")[:100],
                "has_due_at": bool(args.get("due_at")),
                "people": args.get("people", [])
            }
        )
        
        task_result = await self.task_tool.execute({
            "operation": "create_task",
            "user_id": user_id,
            "title": args.get("title", "Sin título"),
            "description": args.get("description"),
            "due_at": args.get("due_at"),
            "people": args.get("people", []),
            "tags": args.get("tags", []),
            "media_path": args.get("media_path")
        })
        
        self.tracer.info(
            "task_created",
            extra={
                "task_id": task_result.get("task_id"),
                "title": args.get("title", "")[:50]
            }
        )
        
        return {"success": True, "task": task_result}
    
    async def _tool_save_note(self, user_id: str, args: dict) -> dict:
        """Save note tool."""
        from app.memory import MemoryItem, MemorySection, MemorySource
        
        content = args.get("content", "")
        
        self.tracer.info(
            "saving_note",
            extra={
                "user_id": user_id,
                "content_length": len(content),
                "content_preview": content[:100],
                "people": args.get("people", []),
                "has_media": bool(args.get("media_path"))
            }
        )
        
        memory_data = {
            "source": MemorySource.CAPTURE,
            "section": MemorySection.NOTE,
            "title": args.get("content", "")[:50],
            "content": args.get("content", ""),
            "people": args.get("people", []),
            "tags": args.get("tags", []),
            "user_id": user_id,
            "metadata": {"agent": "orchestrator"}
        }
        
        if args.get("media_path"):
            memory_data["media_type"] = args.get("media_type")
            memory_data["media_path"] = args.get("media_path")
        
        memory_item = MemoryItem(**memory_data)
        await self.memory.store_memory(memory_item)
        
        self.tracer.info(
            "note_saved",
            extra={
                "title": memory_data["title"],
                "people": memory_data["people"]
            }
        )
        
        return {"success": True}
    
    async def _tool_add_to_list(self, user_id: str, args: dict) -> dict:
        """Add to list tool."""
        list_name = args.get("list_name", "Compras")
        items = args.get("items", [])
        
        if isinstance(items, str):
            items = [items]
        
        self.tracer.info(
            "adding_to_list",
            extra={
                "user_id": user_id,
                "list_name": list_name,
                "items_count": len(items),
                "items": items[:5]  # First 5 items
            }
        )
        
        # First, get or create list
        lists_result = await self.list_tool.execute({
            "operation": "get_lists",
            "user_id": user_id
        })
        
        # Find matching list or create new one
        existing_list = None
        for lst in lists_result.get("lists", []):
            if lst.get("name", "").lower() == list_name.lower():
                existing_list = lst
                break
        
        if not existing_list:
            # Create new list
            create_result = await self.list_tool.execute({
                "operation": "create_list",
                "name": list_name,
                "user_id": user_id
            })
            list_id = create_result.get("list_id")
        else:
            list_id = existing_list.get("id")
        
        # Add items
        for item in items:
            await self.list_tool.execute({
                "operation": "add_item",
                "list_id": list_id,
                "text": item,
                "user_id": user_id
            })
        
        self.tracer.info(
            "items_added_to_list",
            extra={
                "list_name": list_name,
                "items_added": len(items)
            }
        )
        
        return {"success": True, "list_name": list_name, "items": items}
    
    async def _tool_search_memory(self, user_id: str, args: dict) -> dict:
        """
        Search memory tool.
        
        If nothing found in memory, transparently fallback to CHAT mode
        (offering to store or providing general conversation).
        """
        from app.crews.retrieval import RetrievalContext
        
        query = args.get("query", "")
        
        self.tracer.info(
            "searching_memory",
            extra={
                "query": query[:150],
                "user_id": user_id
            }
        )
        
        # Create retrieval context
        context = RetrievalContext(
            user_id=user_id,
            chat_id="orchestrator",  # Generic chat ID for orchestrator calls
            memory_service=self.memory
        )
        
        # Use retrieval crew
        result = self.retrieval_crew.retrieve(query, context)
        
        if not result.memories:
            # No memories found - fallback to chat with context
            self.tracer.info(
                "memory_search_empty",
                extra={
                    "query": query[:100],
                    "memories_found": 0,
                    "will_fallback": True
                }
            )
            
            return {
                "success": True,
                "results": [],
                "fallback_to_chat": True,
                "query": query
            }
        
        # Format memories as results
        results = [
            {
                "title": mem.title,
                "content": mem.content,
                "people": mem.people,
                "created_at": mem.created_at
            }
            for mem in result.memories[:3]
        ]
        
        self.tracer.info(
            "memory_search_found",
            extra={
                "query": query[:100],
                "memories_found": len(result.memories),
                "returned": len(results)
            }
        )
        
        return {"success": True, "results": results}
    
    async def _chat_fallback(self, query: str, user_id: str, context: str) -> dict:
        """
        Fallback to chat when memory search returns empty.
        
        Option 3 (Transparent Fallback):
        - Tell user we didn't find anything
        - Offer to store information
        - Provide helpful general response if appropriate
        """
        
        self.tracer.info(
            "generating_chat_fallback",
            extra={
                "query": query[:150],
                "context": context
            }
        )
        
        prompt = f"""El usuario preguntó: "{query}"

Busqué en la memoria pero NO encontré nada guardado sobre eso.

Tu trabajo:
1. Di que no tienes información guardada sobre eso
2. Ofrece ayuda:
   - Si es pregunta personal (sobre alguien, algo que debería recordar):
     → Pregunta "¿Quieres que guarde algo sobre esto?"
   - Si es pregunta general (opinión, conocimiento general):
     → Responde brevemente + menciona que no tengo info personal guardada

Ejemplos:

Pregunta: "¿Qué me dijo María sobre Barcelona?"
→ "No tengo información guardada sobre eso. ¿Qué te dijo María sobre Barcelona? Te lo guardo si quieres."

Pregunta: "¿Cuándo es el cumpleaños de Juan?"
→ "No tengo el cumpleaños de Juan guardado. ¿Cuándo es? Te lo anoto para recordártelo."

Pregunta: "¿Qué sabes de Barcelona?"
→ "No tengo información personal guardada sobre Barcelona. Es una ciudad increíble con mucha historia. ¿Quieres que guarde algo específico sobre Barcelona?"

Responde en español, natural y conciso."""

        system_prompt = """Asistente conversacional en español.
Respuesta natural cuando no hay información en memoria.
Siempre ofrece guardar información si parece personal.
Sin JSON, solo texto natural."""
        
        try:
            response = self.llm.generate(prompt, system_prompt)
            
            self.tracer.info(
                "chat_fallback_generated",
                extra={
                    "query": query[:100],
                    "response": response[:150]
                }
            )
            
            return {
                "success": True,
                "chat_response": response.strip()
            }
        
        except Exception as e:
            self.tracer.error(
                "chat_fallback_error",
                extra={
                    "query": query[:100],
                    "error": str(e)
                }
            )
            return {
                "success": True,
                "chat_response": f"No encontré información sobre '{query}'. ¿Quieres que guarde algo sobre esto?"
            }
    
    async def _handle_confirmation(
        self, answer: str, context: dict, chat_id: str, user_id: str
    ) -> dict:
        """Handle user confirmation."""
        
        answer_lower = answer.lower().strip()
        
        # Check for affirmative
        if any(word in answer_lower for word in ["sí", "si", "yes", "ok", "vale", "correcto", "exacto"]):
            # Execute action
            result = await self._execute_action(
                context["action_type"],
                context["entities"],
                user_id
            )
            
            # Clear context
            self.contexts.pop(chat_id, None)
            
            return result
        
        # Check for negative
        elif any(word in answer_lower for word in ["no", "nope", "incorrecto", "mal"]):
            # Clear context and ask to rephrase
            self.contexts.pop(chat_id, None)
            return {
                "message": "Ok, entendido. ¿Puedes decirme de nuevo qué quieres hacer?",
                "waiting_for_input": False
            }
        
        else:
            # Unclear response - ask again
            return {
                "message": "No entiendo. ¿Es correcto lo que entendí? (responde sí o no)",
                "waiting_for_input": True
            }
    
    async def _handle_field_answer(
        self, answer: str, media_ref, context: dict, chat_id: str, user_id: str
    ) -> dict:
        """Handle answer providing missing field."""
        
        field = context["waiting_for"]
        action_type = context["action_type"]
        entities = context["entities"]
        
        # Extract value for this field
        extracted = await self._extract_field_value(answer, field, media_ref)
        
        # Add to entities
        entities[field] = extracted
        
        self.tracer.info(
            "field_extracted",
            extra={"field": field, "value": str(extracted)[:100]}
        )
        
        # Check if still missing anything
        still_missing = self._check_missing_fields(action_type, entities)
        
        if still_missing:
            # Ask for next missing field
            return await self._ask_for_missing(
                action_type, entities, still_missing[0], chat_id
            )
        else:
            # Have everything - show understanding and confirm
            return await self._show_understanding_and_confirm(
                action_type, entities, chat_id, user_id
            )
    
    async def _extract_field_value(self, answer: str, field: str, media_ref):
        """Extract field value from user answer."""
        
        # Simple extraction based on field type
        if field == "title":
            return answer.strip()
        
        elif field == "content":
            return answer.strip()
        
        elif field == "items":
            # Split by common separators
            items = [
                item.strip() 
                for item in answer.replace(",", "\n").replace(" y ", "\n").split("\n")
                if item.strip()
            ]
            return items
        
        elif field == "list_name":
            return answer.strip()
        
        elif field == "query":
            return answer.strip()
        
        elif field == "due_at":
            # Keep as string, let temporal tool parse later
            return answer.strip()
        
        else:
            return answer.strip()
    
    async def _execute_action(
        self, action_type: str, entities: dict, user_id: str
    ) -> dict:
        """Execute action using agents as stateless tools."""
        
        self.tracer.info("executing_action", extra={"action": action_type})
        
        try:
            if action_type == "task":
                return await self._execute_task(entities, user_id)
            
            elif action_type == "note":
                return await self._execute_note(entities, user_id)
            
            elif action_type == "list":
                return await self._execute_list(entities, user_id)
            
            elif action_type == "query":
                return await self._execute_query(entities, user_id)
            
            else:
                return {
                    "message": "No pude procesar la acción.",
                    "waiting_for_input": False
                }
        
        except Exception as e:
            self.tracer.error(f"Execution failed: {e}")
            return {
                "message": f"Hubo un error: {str(e)}",
                "waiting_for_input": False
            }
    
    async def _execute_task(self, entities: dict, user_id: str) -> dict:
        """Create task using TaskTool directly."""
        
        task_result = await self.task_tool.execute({
            "operation": "create_task",
            "user_id": user_id,
            "title": entities["title"],
            "description": entities.get("description"),
            "due_at": entities.get("due_at"),
            "people": entities.get("people", []),
            "tags": entities.get("tags", []),
            "media_path": entities.get("media_reference", {}).get("media_path")
        })
        
        task = task_result.get("task", {})
        
        # Generate friendly confirmation
        msg = f"✅ Tarea creada: **{task.get('title', entities['title'])}**"
        if task.get("due_at"):
            msg += f"\n📅 {task.get('due_at')}"
        
        return {"message": msg, "waiting_for_input": False}
    
    async def _execute_note(self, entities: dict, user_id: str) -> dict:
        """Save note using MemoryService directly."""
        
        from app.memory import MemoryItem, MemorySection, MemorySource
        
        media_ref_dict = entities.get("media_reference", {})
        
        memory_data = {
            "source": MemorySource.CAPTURE,
            "section": MemorySection.NOTE,
            "title": entities.get("title", entities["content"][:50]),
            "content": entities["content"],
            "people": entities.get("people", []),
            "tags": entities.get("tags", []),
            "user_id": user_id,
            "metadata": {"agent": "orchestrator"}
        }
        
        # Add media if present
        if media_ref_dict.get("media_path"):
            memory_data["media_type"] = media_ref_dict.get("media_type")
            memory_data["media_path"] = media_ref_dict.get("media_path")
        
        memory_item = MemoryItem(**memory_data)
        await self.memory.store_memory(memory_item)
        
        return {
            "message": f"💾 Nota guardada: {entities['content'][:50]}...",
            "waiting_for_input": False
        }
    
    async def _execute_list(self, entities: dict, user_id: str) -> dict:
        """Add items to list using ListTool."""
        
        list_name = entities.get("list_name", "Compras")  # Default list
        items = entities["items"]
        
        # Get or create list
        lists_result = await self.list_tool.execute({
            "operation": "get_lists",
            "user_id": user_id
        })
        
        # Find matching list or create new one
        existing_list = None
        for lst in lists_result.get("lists", []):
            if lst.get("name", "").lower() == list_name.lower():
                existing_list = lst
                break
        
        if not existing_list:
            # Create new list
            create_result = await self.list_tool.execute({
                "operation": "create_list",
                "name": list_name,
                "user_id": user_id
            })
            list_id = create_result.get("list_id")
        else:
            list_id = existing_list.get("id")
        
        # Add items
        for item in items:
            await self.list_tool.execute({
                "operation": "add_item",
                "list_id": list_id,
                "text": item,
                "user_id": user_id
            })
        
        msg = f"✅ Añadido a {list_name}:\n"
        msg += "\n".join(f"  • {item}" for item in items)
        
        return {"message": msg, "waiting_for_input": False}
    
    async def _execute_query(self, entities: dict, user_id: str) -> dict:
        """
        Search using RetrievalCrew.
        
        If nothing found, fallback to chat (transparent).
        """
        from app.crews.retrieval import RetrievalContext
        
        query = entities["query"]
        
        # Create retrieval context
        context = RetrievalContext(
            user_id=user_id,
            chat_id="orchestrator",
            memory_service=self.memory
        )
        
        # Use retrieval crew to search
        result = self.retrieval_crew.retrieve(query, context)
        
        if not result.memories:
            # No memories - fallback to chat
            self.tracer.info(
                "query_empty_fallback",
                extra={"query": query, "fallback": "chat"}
            )
            
            fallback = await self._chat_fallback(
                query=query,
                user_id=user_id,
                context="Query returned empty, offering to store"
            )
            
            return {
                "message": fallback.get("chat_response", "No encontré nada."),
                "waiting_for_input": False
            }
        
        # Format results
        msg = f"🔍 Encontré esto sobre '{query}':\n\n"
        for i, mem in enumerate(result.memories[:3], 1):
            msg += f"{i}. {mem.title}\n"
            msg += f"   {mem.content[:100]}...\n\n"
        
        return {"message": msg, "waiting_for_input": False}
