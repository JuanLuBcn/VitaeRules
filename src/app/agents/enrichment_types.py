"""Data structures for enrichment conversations."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Callable


@dataclass
class EnrichmentContext:
    """Tracks state of an enrichment conversation."""

    # Original request
    chat_id: str
    user_id: str
    agent_type: str  # "list", "task", "note"
    operation: str  # "add_item", "create_task", etc.
    original_data: dict[str, Any]

    # Enrichment state
    missing_fields: list[str] = field(default_factory=list)
    asked_fields: list[str] = field(default_factory=list)
    gathered_data: dict[str, Any] = field(default_factory=dict)

    # Conversation tracking
    turn_count: int = 0
    max_turns: int = 3  # Don't be annoying
    priority: str = "medium"  # "high", "medium", "low", "skip"

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def is_complete(self) -> bool:
        """Check if enrichment is done."""
        return (
            not self.missing_fields
            or self.turn_count >= self.max_turns
            or self.priority == "skip"
        )

    def next_field_to_ask(self) -> str | None:
        """Get next most valuable field to ask about."""
        for field_name in self.missing_fields:
            if field_name not in self.asked_fields:
                return field_name
        return None

    def mark_field_asked(self, field_name: str) -> None:
        """Mark a field as asked."""
        if field_name not in self.asked_fields:
            self.asked_fields.append(field_name)
        self.turn_count += 1

    def add_gathered_data(self, field_name: str, value: Any) -> None:
        """Add extracted data for a field."""
        self.gathered_data[field_name] = value
        # Remove from missing fields if we got it
        if field_name in self.missing_fields:
            self.missing_fields.remove(field_name)

    def get_final_data(self) -> dict[str, Any]:
        """Merge original data with gathered data."""
        return {**self.original_data, **self.gathered_data}


@dataclass
class EnrichmentRule:
    """Rule for when/how to ask about a field."""

    field_name: str
    agent_types: list[str]  # Which agents this applies to
    priority_fn: Callable[[dict], str]  # Function to determine priority
    question_template: str  # Spanish question
    follow_up: str | None = None  # Optional clarification
    examples: list[str] = field(default_factory=list)  # Example answers

    def should_ask(self, agent_type: str, data: dict) -> bool:
        """Determine if we should ask about this field."""
        if agent_type not in self.agent_types:
            return False

        # Already have this field
        if self.field_name in data and data[self.field_name]:
            return False

        # Check priority
        priority = self.priority_fn(data)
        return priority in ["high", "medium"]

    def get_priority(self, data: dict) -> str:
        """Get priority level for this field."""
        return self.priority_fn(data)


@dataclass
class AgentResponse:
    """Enhanced agent response with enrichment support."""

    message: str  # User-facing message
    success: bool
    needs_enrichment: bool = False  # Whether enrichment is recommended
    extracted_data: dict[str, Any] = field(default_factory=dict)  # Data from user input
    operation: str | None = None  # What operation to perform
    tool_result: dict[str, Any] | None = None  # Result from tool execution
