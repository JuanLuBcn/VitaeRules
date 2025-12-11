"""Note and memory agent."""

from typing import Any

from app.llm import LLMService
from app.memory import MemoryService
from app.tracing import get_tracer

from .base import AgentResult, BaseAgent

logger = get_tracer()


class NoteAgent(BaseAgent):
    """
    Handles saving notes and memories.
    
    Understands:
    - "Remember that John likes coffee"
    - "Note: Meeting went well"
    - "Save this: Project deadline is next Friday"
    - "John's phone number is 555-1234"
    """
    
    def __init__(self, llm_service: LLMService, memory_service: MemoryService):
        """Initialize note agent."""
        super().__init__(llm_service, memory_service)
    
    @property
    def name(self) -> str:
        """Agent name."""
        return "NoteAgent"
    
    @property
    def description(self) -> str:
        """Agent description."""
        return "Saves notes, memories, and facts for later retrieval"
    
    async def can_handle(self, message: str) -> tuple[bool, float]:
        """Check if message is about saving a note."""
        message_lower = message.lower()
        
        # Strong note indicators
        note_words = [
            "remember", "recuerda", "note", "nota", "save", "guarda",
            "don't forget", "no olvides", "keep in mind", "ten en cuenta"
        ]
        if any(word in message_lower for word in note_words):
            return True, 0.9
        
        return False, 0.0
    
    async def handle(
        self,
        message: str,
        chat_id: str,
        user_id: str,
        context: dict[str, Any] | None = None
    ) -> AgentResult:
        """Handle saving a note."""
        logger.info(f"NoteAgent handling: {message[:100]}")
        
        # Extract note details
        note_data = self._extract_note_details(message)
        
        # Add media reference if present
        if context and "media_reference" in context:
            media_ref = context["media_reference"]
            note_data["media_reference"] = media_ref
        
        if not note_data.get("content"):
            return AgentResult(
                success=False,
                message="No pude entender qué guardar. Prueba: 'Recuerda que...'",
                error="No note content found"
            )
        
        # Create preview
        content = note_data["content"]
        title = note_data.get("title", "Nota")
        people = note_data.get("people", [])
        tags = note_data.get("tags", [])
        
        preview = f"💾 **¿Guardar esta nota?**\n\n**Contenido:** {content}"
        
        if people:
            preview += f"\n**Personas:** {', '.join(people)}"
        if tags:
            preview += f"\n**Etiquetas:** {', '.join(tags)}"
        
        # Add media info to preview
        if "media_reference" in note_data:
            from app.utils import format_media_display
            media_display = format_media_display(note_data["media_reference"])
            preview += f"\n**Archivo adjunto:** {media_display}"
        
        # Return with confirmation needed
        return AgentResult(
            success=True,
            message=preview,
            needs_confirmation=True,
            preview=preview,
            data={
                "note_data": note_data,
                "chat_id": chat_id,
                "user_id": user_id,
            }
        )
    
    async def execute_confirmed(self, data: dict[str, Any]) -> AgentResult:
        """Execute confirmed note save."""
        from app.memory import MemoryItem, MemorySection, MemorySource
        
        note_data = data["note_data"]
        chat_id = data["chat_id"]
        user_id = data["user_id"]
        
        try:
            # Prepare memory item data
            # Ensure title is never None - use content truncated as fallback
            title = note_data.get("title")
            if not title:  # Handle None or empty string
                title = note_data["content"][:50]  # First 50 chars as title
            
            memory_data = {
                "source": MemorySource.CAPTURE,
                "section": MemorySection.NOTE,
                "title": title,
                "content": note_data["content"],
                "people": note_data.get("people", []),
                "tags": note_data.get("tags", []),
                "chat_id": chat_id,
                "user_id": user_id,
                "metadata": {"agent": "note_agent"}
            }
            
            # Add media fields if present
            if "media_reference" in note_data:
                media_ref = note_data["media_reference"]
                memory_data["media_type"] = media_ref.media_type
                if media_ref.media_path:
                    memory_data["media_path"] = media_ref.media_path
                if media_ref.latitude is not None and media_ref.longitude is not None:
                    memory_data["coordinates"] = (media_ref.latitude, media_ref.longitude)
                # Store media metadata
                memory_data["metadata"]["media"] = media_ref.to_dict()
            
            # Create memory item
            memory_item = MemoryItem(**memory_data)
            
            # Save to memory service
            self.memory.save_memory(memory_item)
            
            response = "✅ Nota guardada correctamente!"
            
            return AgentResult(success=True, message=response)
            
        except Exception as e:
            logger.error(f"Failed to save note: {e}")
            return AgentResult(
                success=False,
                message=f"No pude guardar la nota. {str(e)}",
                error=str(e)
            )
    
    def _extract_note_details(self, message: str) -> dict[str, Any]:
        """Extract note details from message using LLM."""
        prompt = f"""Extrae los detalles de la nota de este mensaje:

Mensaje: "{message}"

Devuelve JSON:
{{
    "content": "qué guardar (limpio, sin prefijo 'recuerda' o 'nota')",
    "title": "título corto o null",
    "people": ["persona1", "persona2"],
    "places": ["lugar1"],
    "tags": ["etiqueta1", "etiqueta2"]
}}

Ejemplos:
- "Recuerda que a Juan le gusta el café" → {{"content": "A Juan le gusta el café", "people": ["Juan"], "tags": ["preferencia"]}}
- "Nota: La reunión fue bien, Sara estaba contenta" → {{"content": "La reunión fue bien, Sara estaba contenta", "people": ["Sara"], "tags": ["reunión"]}}
- "Barcelona es hermosa" → {{"content": "Barcelona es hermosa", "places": ["Barcelona"], "tags": ["viaje", "opinión"]}}
- "La fecha límite del proyecto es el próximo viernes" → {{"content": "La fecha límite del proyecto es el próximo viernes", "tags": ["fecha límite", "trabajo"]}}"""
        
        try:
            result = self.llm.generate_json(
                prompt=prompt,
                system_prompt="Eres un extractor de detalles de notas. Devuelve SOLO JSON válido."
            )
            
            return {
                "content": result.get("content", message),
                "title": result.get("title"),
                "people": result.get("people", []),
                "places": result.get("places", []),
                "tags": result.get("tags", []),
            }
            
        except Exception as e:
            logger.error(f"Note extraction failed: {e}")
            # Fallback: save entire message
            return {
                "content": message,
                "title": None,
                "people": [],
                "places": [],
                "tags": [],
            }
