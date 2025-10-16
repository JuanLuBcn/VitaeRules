"""Tests for Plan contract schema."""

from datetime import UTC, datetime

import pytest

from app.contracts.plan import (
    Followup,
    IntentType,
    Plan,
    PlanEntities,
    SafetyCheck,
    ToolAction,
)


def test_intent_type_enum():
    """Test IntentType enum values."""
    assert IntentType.TASK_CREATE == "task.create"
    assert IntentType.LIST_ADD == "list.add"
    assert IntentType.MEMORY_NOTE == "memory.note"
    assert IntentType.UNKNOWN == "unknown"


def test_followup_creation():
    """Test creating a Followup."""
    followup = Followup(
        ask="What priority should this task have?",
        field="priority",
    )

    assert followup.ask == "What priority should this task have?"
    assert followup.field == "priority"


def test_tool_action_creation():
    """Test creating a ToolAction."""
    action = ToolAction(
        tool="task_tool",
        params={"operation": "create_task", "title": "Test task"},
    )

    assert action.tool == "task_tool"
    assert action.params["operation"] == "create_task"
    assert action.params["title"] == "Test task"


def test_safety_check_defaults():
    """Test SafetyCheck defaults."""
    safety = SafetyCheck()

    assert safety.blocked is False
    assert safety.reason is None


def test_safety_check_blocked():
    """Test SafetyCheck with blocked plan."""
    safety = SafetyCheck(
        blocked=True,
        reason="Destructive operation requires confirmation",
    )

    assert safety.blocked is True
    assert safety.reason == "Destructive operation requires confirmation"


def test_plan_entities_defaults():
    """Test PlanEntities defaults."""
    entities = PlanEntities()

    assert entities.list_name is None
    assert entities.items == []
    assert entities.title is None
    assert entities.priority is None
    assert entities.person_refs == []
    assert entities.place_refs == []
    assert entities.tags == []


def test_plan_entities_with_data():
    """Test PlanEntities with actual data."""
    due_date = datetime(2025, 10, 17, 15, 0, 0, tzinfo=UTC)

    entities = PlanEntities(
        title="Review PR",
        due_at=due_date,
        priority=2,
        person_refs=["@john", "@jane"],
        tags=["work", "urgent"],
    )

    assert entities.title == "Review PR"
    assert entities.due_at == due_date
    assert entities.priority == 2
    assert len(entities.person_refs) == 2
    assert len(entities.tags) == 2


def test_plan_minimal():
    """Test creating a minimal Plan."""
    plan = Plan(intent=IntentType.TASK_CREATE)

    assert plan.intent == "task.create"
    assert isinstance(plan.entities, PlanEntities)
    assert plan.followups == []
    assert plan.actions == []
    assert plan.safety.blocked is False
    assert plan.confidence == 1.0
    assert plan.reasoning is None


def test_plan_complete():
    """Test creating a complete Plan."""
    plan = Plan(
        intent=IntentType.TASK_CREATE,
        entities=PlanEntities(
            title="Test task",
            priority=1,
        ),
        followups=[
            Followup(ask="When is this due?", field="due_at"),
        ],
        actions=[
            ToolAction(
                tool="task_tool",
                params={"operation": "create_task", "title": "Test task"},
            ),
        ],
        safety=SafetyCheck(blocked=False),
        confidence=0.9,
        reasoning="Clear intent to create a task",
    )

    assert plan.intent == "task.create"
    assert plan.entities.title == "Test task"
    assert len(plan.followups) == 1
    assert len(plan.actions) == 1
    assert plan.confidence == 0.9


def test_plan_json_serialization():
    """Test Plan can be serialized to JSON."""
    plan = Plan(
        intent=IntentType.LIST_ADD,
        entities=PlanEntities(
            list_name="Shopping",
            items=["milk", "bread"],
        ),
        actions=[
            ToolAction(
                tool="list_tool",
                params={"operation": "add_item", "list_name": "Shopping"},
            ),
        ],
    )

    # Test model_dump works
    data = plan.model_dump()

    assert data["intent"] == "list.add"
    assert data["entities"]["list_name"] == "Shopping"
    assert len(data["entities"]["items"]) == 2
    assert len(data["actions"]) == 1


def test_plan_from_dict():
    """Test creating Plan from dictionary."""
    data = {
        "intent": "memory.note",
        "entities": {
            "title": "Meeting notes",
            "description": "Discussed Q4 planning",
            "person_refs": ["@alice"],
        },
        "actions": [
            {
                "tool": "memory_note_tool",
                "params": {"title": "Meeting notes"},
            }
        ],
        "confidence": 0.95,
    }

    plan = Plan(**data)

    assert plan.intent == "memory.note"
    assert plan.entities.title == "Meeting notes"
    assert plan.entities.person_refs == ["@alice"]
    assert plan.confidence == 0.95


def test_plan_confidence_validation():
    """Test confidence must be between 0 and 1."""
    # Valid confidence
    plan = Plan(intent=IntentType.UNKNOWN, confidence=0.5)
    assert plan.confidence == 0.5

    # Invalid confidence (too high) should raise
    with pytest.raises(Exception):  # Pydantic ValidationError
        Plan(intent=IntentType.UNKNOWN, confidence=1.5)

    # Invalid confidence (too low) should raise
    with pytest.raises(Exception):
        Plan(intent=IntentType.UNKNOWN, confidence=-0.1)
