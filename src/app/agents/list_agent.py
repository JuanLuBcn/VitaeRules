"""List management agent."""

import re
from typing import Any

from app.agents.enrichment_types import AgentResponse
from app.llm import LLMService
from app.tools.list_tool import ListTool
from app.tracing import get_tracer

from .base import AgentResult, BaseAgent

logger = get_tracer()


class ListAgent(BaseAgent):
    """
    Handles all list operations.
    
    Supports:
    - Adding items to lists
    - Querying lists
    - Removing items
    """
    
    def __init__(self, llm_service: LLMService, list_tool: ListTool):
        """Initialize list agent."""
        self.llm = llm_service
        self.list_tool = list_tool
    
    @property
    def name(self) -> str:
        """Agent name."""
        return "ListAgent"
    
    @property
    def description(self) -> str:
        """Agent description."""
        return "Manages lists (shopping, grocery, etc.) - add, remove, query items"
    
    async def can_handle(self, message: str) -> tuple[bool, float]:
        """Check if message is about lists."""
        message_lower = message.lower()
        
        # Strong indicators
        if "lista" in message_lower or "list" in message_lower:
            return True, 0.9
        
        return False, 0.0
    
    async def handle(
        self,
        message: str,
        chat_id: str,
        user_id: str,
        context: dict[str, Any] | None = None
    ) -> AgentResult:
        """Handle list operation."""
        logger.info(f"ListAgent handling: {message[:100]}")
        
        # Determine operation type
        operation = self._detect_operation(message)
        
        if operation == "query":
            return await self._handle_query(message, chat_id, user_id)
        elif operation == "add":
            return await self._handle_add(message, chat_id, user_id)
        elif operation == "remove":
            return await self._handle_remove(message, chat_id, user_id)
        else:
            return AgentResult(
                success=False,
                message="No estoy seguro de qué quieres hacer con la lista. Prueba: 'Añade X a la lista' o 'Muéstrame la lista'",
                error="Unknown list operation"
            )
    
    def _detect_operation(self, message: str) -> str:
        """Detect list operation type."""
        message_lower = message.lower()
        
        # Query patterns
        if any(word in message_lower for word in ["qué hay", "muestra", "ver", "show", "what's", "list"]):
            if "?" in message or "qué" in message_lower or "cuál" in message_lower:
                return "query"
        
        # Remove patterns
        if any(word in message_lower for word in ["quita", "elimina", "borra", "remove", "delete"]):
            return "remove"
        
        # Add patterns (default)
        if any(word in message_lower for word in ["añade", "agrega", "add", "put"]):
            return "add"
        
        # Default to query if it's a question
        if "?" in message:
            return "query"
        
        # Default to add
        return "add"
    
    async def _handle_query(
        self, message: str, chat_id: str, user_id: str
    ) -> AgentResult:
        """Handle list query."""
        # Extract list name
        list_name = self._extract_list_name(message)
        
        try:
            if list_name:
                # Query specific list
                result = await self.list_tool.execute({
                    "operation": "list_items",
                    "list_name": list_name,
                })
                
                if result["count"] == 0:
                    response = f"🛒 Tu **{list_name}** está vacía."
                else:
                    items_list = []
                    for item in result["items"]:
                        checkbox = '✅' if item['completed'] else '⬜'
                        text = item['text']
                        media_indicator = self._get_media_indicator(item)
                        items_list.append(f"{checkbox} {text}{media_indicator}")
                    
                    items_text = "\n".join(items_list)
                    response = f"🛒 **{list_name.title()}**:\n\n{items_text}\n\n_{result['count']} elemento(s)_"
            else:
                # Show all lists
                result = await self.list_tool.execute({
                    "operation": "get_lists",
                    "user_id": user_id,
                    "chat_id": chat_id,
                })
                
                if result["count"] == 0:
                    response = "No tienes ninguna lista todavía."
                else:
                    lists_text = "\n".join([f"• {lst['name']}" for lst in result["lists"]])
                    response = f"📋 **Tus Listas** ({result['count']}):\n\n{lists_text}"
            
            return AgentResult(success=True, message=response)
            
        except Exception as e:
            logger.error(f"List query failed: {e}")
            return AgentResult(
                success=False,
                message=f"No pude encontrar la lista '{list_name}'. Prueba añadiendo elementos primero para crearla.",
                error=str(e)
            )
    
    async def _handle_add(
        self, message: str, chat_id: str, user_id: str
    ) -> AgentResponse:
        """Handle adding items to list (with enrichment support)."""
        # Extract items and list name
        items, list_name = self._extract_items_and_list(message)
        
        if not items:
            # Return error as AgentResponse
            return AgentResponse(
                message="No pude encontrar qué elementos añadir. Prueba: 'Añade leche a la lista de la compra'",
                success=False,
                needs_enrichment=False,
            )
        
        # Create preview message
        if len(items) == 1:
            preview = f"✅ Perfecto, agregaré **{items[0]}** a tu {list_name}"
        else:
            preview = f"✅ Perfecto, agregaré {len(items)} elementos a tu {list_name}"
        
        # Return with enrichment support for first item
        # (For multiple items, we'll only enrich the first one for simplicity)
        first_item = items[0]
        
        return AgentResponse(
            message=preview,
            success=True,
            needs_enrichment=True,  # Enable enrichment
            extracted_data={
                "operation": "add_item",
                "list_name": list_name,
                "item_text": first_item,
                "user_id": user_id,
                "chat_id": chat_id,
                # Additional items for batch add (future)
                "remaining_items": items[1:] if len(items) > 1 else [],
            },
            operation="add_item",
        )
    
    async def execute_confirmed(self, data: dict[str, Any]) -> AgentResult:
        """Execute confirmed add operation."""
        items = data["items"]
        list_name = data["list_name"]
        chat_id = data["chat_id"]
        user_id = data["user_id"]
        
        added_count = 0
        
        try:
            for item in items:
                await self.list_tool.execute({
                    "operation": "add_item",
                    "list_name": list_name,
                    "item_text": item,
                    "user_id": user_id,
                    "chat_id": chat_id,
                })
                added_count += 1
                logger.debug(f"Added item: {item}")
            
            if added_count == 1:
                response = f"✅ He añadido **{items[0]}** a tu {list_name}!"
            else:
                response = f"✅ He añadido {added_count} elementos a tu {list_name}!"
            
            return AgentResult(success=True, message=response)
            
        except Exception as e:
            logger.error(f"Failed to add items: {e}")
            return AgentResult(
                success=False,
                message=f"No pude añadir los elementos: {str(e)}",
                error=str(e)
            )
    
    async def _handle_remove(
        self, message: str, chat_id: str, user_id: str
    ) -> AgentResult:
        """Handle removing items from list."""
        try:
            # Extract what to remove and from which list
            items_to_remove, list_name = self._extract_items_for_removal(message)
            
            if not items_to_remove:
                # Check if user wants to clear entire list
                if any(word in message.lower() for word in ["todos", "todo", "all", "everything", "clear", "vacía"]):
                    # Get list name
                    if not list_name:
                        list_name = "Compra"  # Default
                    
                    return AgentResult(
                        success=True,
                        message=f"⚠️ ¿Estás seguro de que quieres eliminar TODOS los elementos de '{list_name}'?",
                        needs_confirmation=True,
                        data={
                            "action": "clear_list",
                            "list_name": list_name,
                            "chat_id": chat_id,
                            "user_id": user_id
                        }
                    )
                
                return AgentResult(
                    success=False,
                    message="No pude entender qué quieres eliminar. Prueba: 'Quita leche de la lista' o 'Elimina todos los artículos'",
                    error="No items to remove found"
                )
            
            # Remove specific items
            result = self.list_tool.remove_items(
                user_id=user_id,
                list_name=list_name or "Compra",
                items=items_to_remove
            )
            
            if result.get("success"):
                removed_count = result.get("removed_count", 0)
                if removed_count > 0:
                    message = f"✅ Eliminé {removed_count} elemento(s) de la lista"
                else:
                    message = "❌ No encontré esos elementos en la lista"
                
                return AgentResult(success=True, message=message)
            else:
                return AgentResult(
                    success=False,
                    message=f"No pude eliminar los elementos: {result.get('error', 'error desconocido')}",
                    error=result.get("error")
                )
                
        except Exception as e:
            logger.error(f"Failed to remove items: {e}")
            return AgentResult(
                success=False,
                message=f"No pude eliminar los elementos: {str(e)}",
                error=str(e)
            )
    
    async def execute_confirmed(self, data: dict[str, Any]) -> AgentResult:
        """Execute confirmed action (like clearing entire list)."""
        try:
            action = data.get("action")
            
            if action == "clear_list":
                list_name = data["list_name"]
                user_id = data["user_id"]
                
                result = self.list_tool.clear_list(
                    user_id=user_id,
                    list_name=list_name
                )
                
                if result.get("success"):
                    return AgentResult(
                        success=True,
                        message=f"✅ Lista '{list_name}' vaciada completamente"
                    )
                else:
                    return AgentResult(
                        success=False,
                        message=f"No pude vaciar la lista: {result.get('error', 'error desconocido')}",
                        error=result.get("error")
                    )
            
            return AgentResult(
                success=False,
                message="Acción no reconocida",
                error="Unknown action"
            )
            
        except Exception as e:
            logger.error(f"Failed to execute confirmed action: {e}")
            return AgentResult(
                success=False,
                message=f"Error al ejecutar acción: {str(e)}",
                error=str(e)
            )
    
    def _extract_items_for_removal(self, message: str) -> tuple[list[str], str]:
        """Extract items to remove and list name."""
        prompt = f"""Extrae qué elementos eliminar y de qué lista:

Mensaje: "{message}"

Devuelve JSON:
{{
    "items": ["item1", "item2"] o [],
    "list_name": "nombre de la lista" o null,
    "clear_all": true/false
}}

Ejemplos:
- "Quita leche de la compra" → {{"items": ["leche"], "list_name": "Compra"}}
- "Elimina pan y huevos" → {{"items": ["pan", "huevos"], "list_name": null}}
- "Borra todos los artículos" → {{"items": [], "clear_all": true}}
"""
        
        try:
            result = self.llm.generate_json(
                prompt=prompt,
                system_prompt="Extrae datos de eliminación de listas. Devuelve SOLO JSON válido."
            )
            
            items = result.get("items", [])
            list_name = result.get("list_name")
            
            return items, list_name
            
        except Exception as e:
            logger.error(f"Item removal extraction failed: {e}")
            return [], None
    
    def _extract_items_and_list(self, message: str) -> tuple[list[str], str]:
        """
        Extract items and list name from message.
        
        Returns:
            (items, list_name)
        """
        # Use LLM to extract structured data
        prompt = f"""Extrae los elementos y el nombre de la lista de este mensaje:

Mensaje: "{message}"

Devuelve JSON:
{{
    "items": ["elemento1", "elemento2", ...],
    "list_name": "nombre de la lista"
}}

Reglas:
- Separa elementos por coma, "y", "and"
- Infiere el nombre de la lista del contexto ("compra" → "lista de la compra", "shopping" → "lista de la compra")
- Si no se menciona nombre de lista, usa "lista de la compra" por defecto"""
        
        try:
            result = self.llm.generate_json(
                prompt=prompt,
                system_prompt="Eres un extractor de datos. Devuelve SOLO JSON válido."
            )
            
            items = result.get("items", [])
            list_name = result.get("list_name", "lista de la compra")
            
            return items, list_name
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            # Fallback: simple regex parsing
            items = self._parse_items_simple(message)
            list_name = self._extract_list_name(message) or "lista de la compra"
            return items, list_name
    
    def _parse_items_simple(self, text: str) -> list[str]:
        """Simple fallback item parsing."""
        # Remove common list-related words
        clean = re.sub(r'\b(añade|add|a la lista|to the list|de la compra|shopping)\b', '', text, flags=re.IGNORECASE)
        
        # Split by comma, "y", "and"
        items = re.split(r'[,;]|\s+y\s+|\s+and\s+', clean)
        items = [item.strip() for item in items if item.strip()]
        
        return items
    
    def _get_media_indicator(self, item: dict[str, Any]) -> str:
        """Get media indicator emoji for a list item."""
        media_path = item.get("media_path")
        if not media_path:
            return ""
        
        # Determine media type from metadata or path
        metadata = item.get("metadata", {})
        if isinstance(metadata, str):
            try:
                import json
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        media_info = metadata.get("media", {})
        media_type = media_info.get("media_type")
        
        # Fallback: detect from file extension
        if not media_type and media_path:
            if "photos" in media_path or media_path.endswith((".jpg", ".jpeg", ".png")):
                media_type = "photo"
            elif "voice" in media_path or media_path.endswith((".ogg", ".mp3", ".wav")):
                media_type = "voice"
            elif "documents" in media_path:
                media_type = "document"
        
        # Return appropriate emoji
        if media_type == "photo":
            return " 📷"
        elif media_type == "voice":
            return " 🎤"
        elif media_type == "document":
            return " 📄"
        else:
            return " 📎"  # Generic attachment
    
    def _extract_list_name(self, message: str) -> str | None:
        """Extract list name from message."""
        message_lower = message.lower()
        
        # Common list names
        if "compra" in message_lower or "shopping" in message_lower:
            return "lista de la compra"
        elif "grocery" in message_lower or "groceries" in message_lower:
            return "lista de la compra"
        
        # Generic patterns
        patterns = [
            r"lista (?:de )?(\w+)",
            r"(\w+) list",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_lower)
            if match:
                return match.group(0)
        
        return None
