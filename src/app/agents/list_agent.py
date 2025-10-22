"""List management agent."""

import re
from typing import Any

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
                    items_text = "\n".join([
                        f"{'✅' if item['completed'] else '⬜'} {item['text']}"
                        for item in result["items"]
                    ])
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
    ) -> AgentResult:
        """Handle adding items to list."""
        # Extract items and list name
        items, list_name = self._extract_items_and_list(message)
        
        if not items:
            return AgentResult(
                success=False,
                message="No pude encontrar qué elementos añadir. Prueba: 'Añade leche a la lista de la compra'",
                error="No items extracted"
            )
        
        # Create preview
        if len(items) == 1:
            preview = f"🛒 ¿Añadir **{items[0]}** a tu {list_name}?"
        else:
            items_list = "\n".join([f"  • {item}" for item in items])
            preview = f"🛒 ¿Añadir {len(items)} elementos a tu {list_name}?\n\n{items_list}"
        
        # Return with confirmation needed
        return AgentResult(
            success=True,
            message=preview,
            needs_confirmation=True,
            preview=preview,
            data={
                "items": items,
                "list_name": list_name,
                "operation": "add",
                "chat_id": chat_id,
                "user_id": user_id,
            }
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
        return AgentResult(
            success=False,
            message="La función de eliminar elementos aún no está implementada.",
            error="Not implemented"
        )
    
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
