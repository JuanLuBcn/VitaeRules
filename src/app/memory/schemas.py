"""Memory-related pydantic schemas."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MemorySource(str, Enum):
    """Source of a memory item."""

    CAPTURE = "capture"
    DIARY = "diary"
    IMPORT = "import"
    SYSTEM = "system"


class MemorySection(str, Enum):
    """Section/category of a memory item."""

    EVENT = "event"
    NOTE = "note"
    DIARY = "diary"
    TASK = "task"
    LIST = "list"
    REMINDER = "reminder"
    CONVERSATION = "conversation"


class MemoryStatus(str, Enum):
    """Status of a memory item."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class MemoryItem(BaseModel):
    """Long-term memory item with rich metadata."""

    # Core fields
    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    source: MemorySource = Field(description="Where this memory came from")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last update timestamp",
    )

    # Content
    title: str = Field(description="Short title/summary")
    content: str = Field(description="Full content/description")
    tags: list[str] = Field(default_factory=list, description="User-defined tags")

    # People and social
    people: list[str] = Field(default_factory=list, description="People mentioned (@name)")
    attendees: list[str] = Field(default_factory=list, description="Event attendees")

    # Temporal
    event_start_at: datetime | None = Field(default=None, description="Event start time")
    event_end_at: datetime | None = Field(default=None, description="Event end time")
    timezone: str | None = Field(default=None, description="Timezone for temporal fields")
    date_bucket: str | None = Field(
        default=None, description="Date bucket for retrieval (YYYY-MM-DD)"
    )

    # Location
    location: str | None = Field(default=None, description="Location/place name")
    coordinates: tuple[float, float] | None = Field(
        default=None, description="(latitude, longitude)"
    )

    # Media and attachments
    media_type: str | None = Field(default=None, description="MIME type of media")
    media_path: str | None = Field(default=None, description="Path to media file")
    attachments: list[str] = Field(default_factory=list, description="Attachment file paths")

    # Classification
    section: MemorySection = Field(
        default=MemorySection.NOTE, description="Memory section/category"
    )
    status: MemoryStatus = Field(default=MemoryStatus.ACTIVE, description="Item status")

    # External references
    external_id: str | None = Field(
        default=None, description="External system ID (Google Calendar, etc.)"
    )
    external_url: str | None = Field(default=None, description="External URL reference")

    # Task/reminder specific
    due_at: datetime | None = Field(default=None, description="Due date for tasks")
    completed_at: datetime | None = Field(default=None, description="Completion timestamp")
    list_name: str | None = Field(default=None, description="List this item belongs to")

    # User context
    chat_id: str | None = Field(default=None, description="Chat/conversation ID")
    user_id: str | None = Field(default=None, description="User ID who created this")

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = {
        "use_enum_values": True,
    }


class ConversationMessage(BaseModel):
    """A single message in a conversation (STM)."""

    id: UUID = Field(default_factory=uuid4, description="Message ID")
    chat_id: str = Field(description="Chat/conversation identifier")
    user_id: str | None = Field(default=None, description="User who sent the message")
    role: str = Field(description="Message role (user, assistant, system)")
    content: str = Field(description="Message content")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Message timestamp",
    )
    correlation_id: str | None = Field(default=None, description="Trace correlation ID")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class MemoryQuery(BaseModel):
    """Query for retrieving memories."""

    query: str = Field(description="Natural language query or search text")
    top_k: int = Field(default=4, description="Number of results to return")
    filters: dict[str, Any] = Field(default_factory=dict, description="Metadata filters")
    section: MemorySection | None = Field(default=None, description="Filter by section")
    start_date: datetime | None = Field(default=None, description="Filter by start date")
    end_date: datetime | None = Field(default=None, description="Filter by end date")
    people: list[str] | None = Field(default=None, description="Filter by people")
    tags: list[str] | None = Field(default=None, description="Filter by tags")


class MemorySearchResult(BaseModel):
    """A single search result from memory."""

    item: MemoryItem = Field(description="The memory item")
    score: float = Field(description="Relevance score (0-1)")
    highlights: list[str] = Field(default_factory=list, description="Matching text snippets")
