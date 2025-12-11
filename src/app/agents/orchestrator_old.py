"""
Example integration of new agent-based architecture.

This shows the simplified flow:
1. Classify intent
2. Route to specialized agent
3. Handle enrichment if needed (NEW)
4. Handle confirmation if needed
5. Execute and return result
"""

from app.agents import (
    IntentClassifier,
    IntentType,
    ListAgent,
    NoteAgent,
    QueryAgent,
    TaskAgent,
)
from app.agents.enrichment_agent import EnrichmentAgent
from app.agents.enrichment_types import AgentResponse
from app.llm import LLMService
from app.memory import MemoryService
from app.tools.list_tool import ListTool
from app.tools.task_tool import TaskTool
from app.crews.retrieval import RetrievalCrew
from app.tracing import get_tracer
from app.utils import extract_media_reference, MediaReference


class AgentOrchestrator:
    """
    Simplified orchestrator that routes messages to specialized agents.
    
    Supports multi-turn enrichment conversations to gather additional context.
    """
    
    def __init__(self, llm_service: LLMService, memory_service: MemoryService):
        """Initialize orchestrator with all agents."""
        self.llm_service = llm_service
        self.memory_service = memory_service
        self.tracer = get_tracer()
        
        self.classifier = IntentClassifier(llm_service)
        
        # Initialize tools and crews
        self.list_tool = ListTool()
        self.task_tool = TaskTool()
        retrieval_crew = RetrievalCrew(memory_service=memory_service)
        
        # Initialize specialized agents
        self.agents = {
            IntentType.LIST: ListAgent(llm_service, self.list_tool),
            IntentType.TASK: TaskAgent(llm_service, self.task_tool),
            IntentType.NOTE: NoteAgent(llm_service, memory_service),
            IntentType.QUERY: QueryAgent(memory_service, retrieval_crew),
        }
        
        # Initialize enrichment agent
        self.enrichment_agent = EnrichmentAgent(llm_service)
        
        # Track pending confirmations per chat
        self.pending_confirmations = {}
    
    async def handle_message(
        self, message: str, chat_id: str, user_id: str
    ) -> dict:
        """
        Handle incoming message.
        
        Returns:
            dict with:
                - message: Response to show user
                - needs_confirmation: bool
                - needs_enrichment: bool (NEW)
                - data: Optional data for confirmation
                - media_reference: Optional media metadata
        """
        # Step 0: Extract media reference if present
        clean_message, media_ref = extract_media_reference(message)
        
        if media_ref:
            self.tracer.info(f"Media detected: {media_ref.media_type}")
        
        # Use clean message for classification and processing
        processing_message = clean_message if media_ref else message
        
        # Step 1: Check if we're in an enrichment conversation
        if await self.enrichment_agent.state_manager.has_context(chat_id):
            return await self._handle_enrichment_response(processing_message, chat_id)
        
        # Step 2: Check for pending confirmation
        if chat_id in self.pending_confirmations:
            return await self._handle_confirmation(processing_message, chat_id, user_id)
        
        # Step 3: Classify intent
        intent, confidence = await self.classifier.classify(processing_message)
        
        # Step 4: Low confidence? Ask for clarification
        if confidence < 0.7:
            return {
                "message": self._build_clarification_message(intent, confidence),
                "needs_confirmation": False,
                "needs_enrichment": False,
            }
        
        # Step 5: Unknown intent?
        if intent == IntentType.UNKNOWN:
            return {
                "message": "No estoy seguro de qué quieres que haga. Prueba: 'Recuerda que...', 'Añade a la lista...', 'Recuérdame...', o haz una pregunta.",
                "needs_confirmation": False,
                "needs_enrichment": False,
            }
        
        # Step 6: Route to specialized agent
        agent = self.agents.get(intent)
        if not agent:
            return {
                "message": f"El agente para {intent} aún no está implementado.",
                "needs_confirmation": False,
                "needs_enrichment": False,
            }
        
        # Pass media reference in context if present
        context = {"media_reference": media_ref} if media_ref else None
        result = await agent.handle(processing_message, chat_id, user_id, context=context)
        
        # Step 7: Check if result supports enrichment
        if isinstance(result, AgentResponse) and result.needs_enrichment:
            return await self._handle_enrichment_start(
                result, intent, chat_id, user_id
            )
        
        # Step 8: Need confirmation? (legacy support)
        if hasattr(result, 'needs_confirmation') and result.needs_confirmation:
            self.pending_confirmations[chat_id] = {
                "agent": agent,
                "data": result.data if hasattr(result, 'data') else {},
            }
            preview_msg = result.preview if hasattr(result, 'preview') else result.message
            return {
                "message": preview_msg,
                "needs_confirmation": True,
                "needs_enrichment": False,
            }
        
        # Step 9: Return result
        return {
            "message": result.message,
            "needs_confirmation": False,
            "needs_enrichment": False,
            "success": result.success,
            "error": result.error if hasattr(result, 'error') else None,
        }
    
    async def _handle_confirmation(
        self, message: str, chat_id: str, user_id: str
    ) -> dict:
        """Handle confirmation response (yes/no)."""
        message_lower = message.lower()
        
        # Get pending action
        pending = self.pending_confirmations.get(chat_id)
        if not pending:
            return {
                "message": "No hay ninguna acción pendiente de confirmar.",
                "needs_confirmation": False,
            }
        
        # Check if user confirmed
        confirmed = any(
            word in message_lower for word in ["yes", "sí", "si", "ok", "claro", "confirma", "vale"]
        )
        
        if not confirmed:
            # User cancelled
            del self.pending_confirmations[chat_id]
            return {
                "message": "Acción cancelada.",
                "needs_confirmation": False,
            }
        
        # Execute confirmed action
        agent = pending["agent"]
        data = pending["data"]
        
        result = await agent.execute_confirmed(data)
        
        # Clear pending
        del self.pending_confirmations[chat_id]
        
        return {
            "message": result.message,
            "needs_confirmation": False,
            "success": result.success,
            "error": result.error,
        }
    
    def _build_clarification_message(self, intent: IntentType, confidence: float) -> str:
        """Build clarification message when confidence is low."""
        return f"""No estoy muy seguro de qué quieres que haga (confianza: {confidence:.0%}).

¿Querías:
• 📝 Guardar una nota o memoria?
• ✅ Crear o gestionar una tarea?
• 📋 Añadir algo a una lista?
• ❓ Hacer una pregunta sobre tus datos?

Por favor, intenta de nuevo con más detalle."""

    async def _handle_enrichment_start(
        self, agent_response: AgentResponse, intent: IntentType, chat_id: str, user_id: str
    ) -> dict:
        """
        Start enrichment conversation.
        
        Args:
            agent_response: Response from agent with needs_enrichment=True
            intent: Intent type that triggered this
            chat_id: Chat identifier
            user_id: User identifier
            
        Returns:
            Response dict with enrichment question
        """
        self.tracer.info(f"Starting enrichment for {intent.value}")
        
        # Map intent to agent type name
        agent_type_map = {
            IntentType.LIST: "list",
            IntentType.TASK: "task",
            IntentType.NOTE: "note",
        }
        agent_type = agent_type_map.get(intent, "unknown")
        
        # Start enrichment
        enrichment_response = await self.enrichment_agent.analyze_and_start(
            agent_type=agent_type,
            operation=agent_response.operation,
            data=agent_response.extracted_data,
            chat_id=chat_id,
        )
        
        if enrichment_response:
            # Show preview message + enrichment question
            full_message = agent_response.message
            if enrichment_response.message:
                full_message += f"\n\n{enrichment_response.message}"
            
            return {
                "message": full_message,
                "needs_confirmation": False,
                "needs_enrichment": True,
                "success": True,
            }
        
        # No enrichment needed, execute immediately
        return await self._execute_tool_operation(agent_response, intent, chat_id, user_id)
    
    async def _handle_enrichment_response(self, message: str, chat_id: str) -> dict:
        """
        Handle user's response in an enrichment conversation.
        
        Args:
            message: User's response
            chat_id: Chat identifier
            
        Returns:
            Response dict with next question or completion
        """
        self.tracer.debug(f"Processing enrichment response for chat {chat_id}")
        
        # Process the response
        enrichment_response = await self.enrichment_agent.process_response(
            message, chat_id
        )
        
        # Check if enrichment is complete
        if not enrichment_response.needs_enrichment:
            # Enrichment complete, execute the tool
            context = await self.enrichment_agent.state_manager.get_context(chat_id)
            
            if context:
                # Get final enriched data
                final_data = enrichment_response.extracted_data
                
                # Map agent type to intent
                agent_type_to_intent = {
                    "list": IntentType.LIST,
                    "task": IntentType.TASK,
                    "note": IntentType.NOTE,
                }
                intent = agent_type_to_intent.get(context.agent_type, IntentType.UNKNOWN)
                
                # Create an AgentResponse for tool execution
                agent_response = AgentResponse(
                    message=enrichment_response.message,
                    success=True,
                    extracted_data=final_data,
                    operation=context.operation,
                )
                
                # Execute tool with enriched data
                result = await self._execute_tool_operation(
                    agent_response, intent, chat_id, final_data.get("user_id", "")
                )
                
                # Combine enrichment message with result
                combined_message = f"{enrichment_response.message}\n\n{result['message']}"
                result["message"] = combined_message
                
                return result
        
        # Still gathering information
        return {
            "message": enrichment_response.message,
            "needs_confirmation": False,
            "needs_enrichment": True,
            "success": True,
        }
    
    async def _execute_tool_operation(
        self, agent_response: AgentResponse, intent: IntentType, chat_id: str, user_id: str
    ) -> dict:
        """
        Execute tool operation with (possibly enriched) data.
        
        Args:
            agent_response: Response containing operation and data
            intent: Intent type
            chat_id: Chat identifier
            user_id: User identifier
            
        Returns:
            Response dict with execution result
        """
        self.tracer.info(f"Executing tool operation: {agent_response.operation}")
        
        try:
            # Get the appropriate tool
            if intent == IntentType.LIST:
                tool = self.list_tool
            elif intent == IntentType.TASK:
                tool = self.task_tool
            else:
                # For NOTE and QUERY, agents handle execution themselves
                return {
                    "message": agent_response.message,
                    "needs_confirmation": False,
                    "needs_enrichment": False,
                    "success": True,
                }
            
            # Prepare data for tool execution
            tool_data = dict(agent_response.extracted_data)
            
            # Convert media_reference to media_path if present
            if "media_reference" in tool_data:
                media_ref = tool_data.pop("media_reference")
                if hasattr(media_ref, 'media_path') and media_ref.media_path:
                    tool_data["media_path"] = media_ref.media_path
                if hasattr(media_ref, 'latitude') and media_ref.latitude is not None:
                    tool_data["latitude"] = media_ref.latitude
                    tool_data["longitude"] = media_ref.longitude
            
            # Execute the tool
            result = await tool.execute(tool_data)
            
            # Build success message
            if intent == IntentType.LIST:
                item_text = agent_response.extracted_data.get("item_text", "item")
                message = f"✅ Agregué '{item_text}' a la lista"
                
                # Add media indicator if present
                if "media_reference" in agent_response.extracted_data:
                    media_ref = agent_response.extracted_data["media_reference"]
                    media_type = getattr(media_ref, 'media_type', None)
                    if media_type == "photo":
                        message += " 📷"
                    elif media_type == "voice":
                        message += " 🎤"
                    elif media_type == "document":
                        message += " 📄"
                
                # Add enrichment details if present
                if agent_response.extracted_data.get("location"):
                    message += f" (📍 {agent_response.extracted_data['location']})"
                if agent_response.extracted_data.get("people"):
                    people = agent_response.extracted_data["people"]
                    if isinstance(people, list):
                        message += f" (👥 {', '.join(people)})"
                
            elif intent == IntentType.TASK:
                title = agent_response.extracted_data.get("title", "tarea")
                message = f"✅ Creé la tarea '{title}'"
                
                # Add media indicator if present
                if "media_reference" in agent_response.extracted_data:
                    media_ref = agent_response.extracted_data["media_reference"]
                    media_type = getattr(media_ref, 'media_type', None)
                    if media_type == "photo":
                        message += " 📷"
                    elif media_type == "voice":
                        message += " 🎤"
                    elif media_type == "document":
                        message += " 📄"
                
                # Add enrichment details
                if agent_response.extracted_data.get("due_at"):
                    message += f" (📅 {agent_response.extracted_data['due_at']})"
                if agent_response.extracted_data.get("location"):
                    message += f" (📍 {agent_response.extracted_data['location']})"
            
            return {
                "message": message,
                "needs_confirmation": False,
                "needs_enrichment": False,
                "success": True,
            }
            
        except Exception as e:
            self.tracer.error(f"Tool execution failed: {e}")
            return {
                "message": f"❌ Error al ejecutar la operación: {str(e)}",
                "needs_confirmation": False,
                "needs_enrichment": False,
                "success": False,
                "error": str(e),
            }


# Example usage
async def example():
    """Example of using the new agent system."""
    llm = LLMService()
    memory = MemoryService()
    orchestrator = AgentOrchestrator(llm, memory)
    
    # Example 1: Add to list
    result = await orchestrator.handle_message(
        message="Añade mantequilla a la lista de la compra",
        chat_id="123",
        user_id="user1",
    )
    print(f"Response: {result['message']}")
    print(f"Needs confirmation: {result['needs_confirmation']}")
    
    # Confirm
    if result["needs_confirmation"]:
        confirm_result = await orchestrator.handle_message(
            message="yes",
            chat_id="123",
            user_id="user1",
        )
        print(f"After confirmation: {confirm_result['message']}")
    
    # Example 2: Create task
    result = await orchestrator.handle_message(
        message="Remind me to call John tomorrow",
        chat_id="123",
        user_id="user1",
    )
    print(f"Response: {result['message']}")
    
    # Example 3: Save note
    result = await orchestrator.handle_message(
        message="Remember that John likes coffee",
        chat_id="123",
        user_id="user1",
    )
    print(f"Response: {result['message']}")
    
    # Example 4: Query
    result = await orchestrator.handle_message(
        message="What did I save about John?",
        chat_id="123",
        user_id="user1",
    )
    print(f"Response: {result['message']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example())
