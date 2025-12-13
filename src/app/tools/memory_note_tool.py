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
                    "enum": ["event", "note", "diary", "task", "list", "reminder", "conversation"],
                    "description": "Memory section/category. Use 'note' for personal information about people, 'event' for scheduled events with dates, 'task' for todos, 'diary' for daily reflections.",
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
                    "description": "Event start time. Prefer ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS). Also accepts formats like DD/MM/YYYY or DD/MM/YY.",
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

        # Parse section with validation
        section_str = arguments.get("section", "note")
        try:
            section = MemorySection(section_str)
        except ValueError:
            # Fallback to 'note' for invalid sections (e.g., 'person')
            self.tracer.warning(f"Invalid section '{section_str}', using 'note' instead")
            section = MemorySection.NOTE

        # Parse event_start_at if provided
        from datetime import datetime
        from dateutil import parser as date_parser

        event_start_at = None
        if "event_start_at" in arguments:
            try:
                # Try ISO format first (preferred)
                event_start_at = datetime.fromisoformat(arguments["event_start_at"])
            except (ValueError, TypeError):
                try:
                    # Fall back to flexible date parsing for formats like "27/08/25", "21/06/2021"
                    event_start_at = date_parser.parse(arguments["event_start_at"], dayfirst=True)
                    self.tracer.debug(f"Parsed date with flexible parser: {arguments['event_start_at']} -> {event_start_at}")
                except Exception as e:
                    self.tracer.error(f"Failed to parse date '{arguments['event_start_at']}': {e}")
                    # Continue without date rather than failing the entire memory save
                    event_start_at = None

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
