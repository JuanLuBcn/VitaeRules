"""Plan contract schema for Capture Crew.

This module defines the Plan structure that the PlannerAgent produces
to represent user intent, extracted entities, and proposed tool actions.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """Supported intent types for the Capture Crew."""

    # Task operations
    TASK_CREATE = "task.create"
    TASK_COMPLETE = "task.complete"
    TASK_UPDATE = "task.update"
    TASK_DELETE = "task.delete"

    # List operations
    LIST_CREATE = "list.create"
    LIST_DELETE = "list.delete"
    LIST_ADD = "list.add"
    LIST_REMOVE = "list.remove"
    LIST_ITEM_COMPLETE = "list.item.complete"

    # Reminder operations
    REMINDER_SCHEDULE = "reminder.schedule"
    REMINDER_CANCEL = "reminder.cancel"

    # Memory operations
    MEMORY_NOTE = "memory.note"

    # Diary operations
    DIARY_ENTRY = "diary.entry"

    # Query operations
    COMMAND_QUERY = "command.query"

    # Unknown intent
    UNKNOWN = "unknown"


class Followup(BaseModel):
    """A clarification question to ask the user."""

    ask: str = Field(description="The question to ask")
    field: str = Field(description="The field this question clarifies")


class ToolAction(BaseModel):
    """A proposed tool action."""

    tool: str = Field(description="Tool name from registry")
    params: dict = Field(description="Tool-specific parameters")


class SafetyCheck(BaseModel):
    """Safety validation for the plan."""

    blocked: bool = Field(default=False, description="Whether plan is blocked")
    reason: str | None = Field(default=None, description="Reason for blocking")


class PlanEntities(BaseModel):
    """Extracted entities from user input."""

    # List/Task context
    list_name: str | None = Field(default=None, description="List name")
    items: list[str] = Field(default_factory=list, description="List items")
    title: str | None = Field(default=None, description="Task/note title")

    # Temporal entities
    due_at: datetime | None = Field(
        default=None, description="Due date/time (ISO format)"
    )
    happened_at: datetime | None = Field(
        default=None, description="Event date/time (ISO format)"
    )

    # Priority
    priority: int | None = Field(default=None, description="Task priority (0-3)")

    # References
    person_refs: list[str] = Field(
        default_factory=list, description="Mentioned people"
    )
    place_refs: list[str] = Field(default_factory=list, description="Mentioned places")
    tags: list[str] = Field(default_factory=list, description="Extracted tags")

    # Content
    description: str | None = Field(default=None, description="Full description")
    section: str | None = Field(
        default=None, description="Memory section (for notes)"
    )


class Plan(BaseModel):
    """Plan produced by PlannerAgent.

    Represents the interpretation of user input as actionable intent,
    extracted entities, and proposed tool calls.
    """

    intent: IntentType = Field(description="Primary intent of user input")
    entities: PlanEntities = Field(
        default_factory=PlanEntities, description="Extracted entities"
    )
    followups: list[Followup] = Field(
        default_factory=list, description="Clarification questions"
    )
    actions: list[ToolAction] = Field(
        default_factory=list, description="Proposed tool actions"
    )
    safety: SafetyCheck = Field(
        default_factory=SafetyCheck, description="Safety validation"
    )
    confidence: float = Field(
        default=1.0, description="Planner confidence (0.0-1.0)", ge=0.0, le=1.0
    )
    reasoning: str | None = Field(
        default=None, description="Planner's reasoning (for debugging)"
    )

    model_config = {"use_enum_values": True}
