"""MemoryNoteTool for creating memory notes."""

from typing import Any

from ..contracts import BaseTool
from ..memory import MemoryItem, MemorySection, MemoryService, MemorySource
from ..tracing import get_tracer


class MemoryNoteTool(BaseTool):
    """
    Tool for creating memory notes with rich metadata.

    Wraps the Memory API to provide a tool interface for agents.
    """

    def __init__(self, memory_service: MemoryService | None = None):
        """
        Initialize MemoryNoteTool.

        Args:
            memory_service: Memory service instance (default: create new)
        """
        self.tracer = get_tracer()
        self.memory_service = memory_service or MemoryService()

        self.tracer.debug("MemoryNoteTool initialized")

    @property
    def name(self) -> str:
        """Tool name."""
        return "memory_note_tool"

    @property
    def description(self) -> str:
        """Tool description."""
        return (
            "Create memory notes with rich metadata (people, location, tags, events). "
            "Notes are stored in long-term memory and can be searched semantically."
        )

    @property
    def schema(self) -> dict[str, Any]:
        """JSON Schema for tool arguments."""
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Note title (brief summary)",
                },
                "content": {
                    "type": "string",
                    "description": "Note content (full text)",
                },
                "section": {
                    "type": "string",
                    "enum": ["note", "event", "person", "project", "reference", "idea"],
                    "description": "Type of memory item",
                },
                "people": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "People mentioned in the note",
                },
                "location": {
                    "type": "string",
                    "description": "Location related to the note",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorization",
                },
                "event_start_at": {
                    "type": "string",
                    "description": "Event start time (ISO format) if this is an event",
                },
                "timezone": {
                    "type": "string",
                    "description": "Timezone for the event",
                },
                "user_id": {
                    "type": "string",
                    "description": "User identifier",
                },
                "chat_id": {
                    "type": "string",
                    "description": "Chat identifier",
                },
            },
            "required": ["title", "content"],
        }

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Create a memory note."""
        title = arguments["title"]
        content = arguments["content"]

        # Parse section
        section_str = arguments.get("section", "note")
        section = MemorySection(section_str)

        # Parse event_start_at if provided
        from datetime import datetime

        event_start_at = None
        if "event_start_at" in arguments:
            event_start_at = datetime.fromisoformat(arguments["event_start_at"])

        # Create memory item
        item = MemoryItem(
            source=MemorySource.CAPTURE,
            title=title,
            content=content,
            section=section,
            people=arguments.get("people", []),
            location=arguments.get("location"),
            tags=arguments.get("tags", []),
            event_start_at=event_start_at,
            timezone=arguments.get("timezone"),
            user_id=arguments.get("user_id"),
            chat_id=arguments.get("chat_id"),
        )

        # Save to memory
        saved_item = self.memory_service.save_memory(item)

        self.tracer.info(f"Created memory note: {title} (id={saved_item.id})")

        return {
            "memory_id": str(saved_item.id),
            "title": saved_item.title,
            "section": saved_item.section,
            "created_at": saved_item.created_at.isoformat(),
            "success": True,
        }
