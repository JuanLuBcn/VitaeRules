"""Integration tests for the Capture Crew."""


import pytest

from app.contracts.plan import IntentType, Plan, PlanEntities, ToolAction
from app.contracts.tools import ToolStatus
from app.crews.capture.clarifier import update_plan_with_answers
from app.crews.capture.crew import CaptureContext, CaptureCrew
from app.crews.capture.tool_caller import execute_plan_actions, format_results_summary
from app.memory.api import MemoryService
from app.tools.registry import get_registry


@pytest.fixture
def test_data_dir(tmp_path):
    """Create a temporary directory for test data."""
    return tmp_path


@pytest.fixture
def register_tools(test_data_dir):
    """Register tools for testing."""
    from app.tools.list_tool import ListTool
    from app.tools.task_tool import TaskTool

    registry = get_registry()

    # Register tools with unique DB paths
    task_tool = TaskTool(db_path=test_data_dir / "test_tasks.sqlite")
    list_tool = ListTool(db_path=test_data_dir / "test_lists.sqlite")

    registry.register(task_tool)
    registry.register(list_tool)

    yield registry

    # Cleanup
    registry._tools.clear()


@pytest.fixture
def memory_service(test_data_dir):
    """Create a MemoryService for testing."""
    from app.memory.long_term import LongTermMemory
    from app.memory.short_term import ShortTermMemory

    stm = ShortTermMemory(db_path=test_data_dir / "test_stm.sqlite")
    ltm = LongTermMemory(store_path=test_data_dir / "test_ltm")

    return MemoryService(stm=stm, ltm=ltm)


@pytest.fixture
def capture_crew(memory_service):
    """Create a CaptureCrew for testing."""
    return CaptureCrew(memory_service=memory_service)


@pytest.fixture
def capture_context():
    """Create a CaptureContext for testing."""
    return CaptureContext(
        chat_id="test_chat",
        user_id="test_user",
        auto_approve=True,  # Auto-approve for testing
    )


@pytest.mark.asyncio
async def test_execute_plan_simple_task(test_data_dir, register_tools):
    """Test executing a simple task creation plan."""
    plan = Plan(
        intent=IntentType.TASK_CREATE,
        entities=PlanEntities(title="Test task"),
        actions=[
            ToolAction(
                tool="task_tool",
                params={"operation": "create_task", "title": "Test task"},
            ),
        ],
    )

    results = await execute_plan_actions(
        plan=plan,
        chat_id="test_chat",
        user_id="test_user",
        auto_approve=True,
    )

    assert len(results) == 1
    assert results[0].status == ToolStatus.SUCCESS
    assert results[0].data is not None
    assert "task_id" in results[0].data


@pytest.mark.asyncio
async def test_execute_plan_no_actions():
    """Test executing a plan with no actions."""
    plan = Plan(intent=IntentType.UNKNOWN)

    results = await execute_plan_actions(
        plan=plan,
        chat_id="test_chat",
        user_id="test_user",
        auto_approve=True,
    )

    assert len(results) == 0


@pytest.mark.asyncio
async def test_execute_plan_blocked():
    """Test executing a blocked plan."""
    plan = Plan(
        intent=IntentType.TASK_DELETE,
        actions=[
            ToolAction(tool="task_tool", params={"operation": "delete_task"}),
        ],
    )
    plan.safety.blocked = True
    plan.safety.reason = "Missing task ID"

    results = await execute_plan_actions(
        plan=plan,
        chat_id="test_chat",
        user_id="test_user",
        auto_approve=True,
    )

    assert len(results) == 1
    assert results[0].status == ToolStatus.ERROR
    assert "blocked" in results[0].error.lower()


@pytest.mark.asyncio
async def test_execute_plan_list_creation(test_data_dir, register_tools):
    """Test executing a list creation plan."""
    plan = Plan(
        intent=IntentType.LIST_CREATE,
        entities=PlanEntities(list_name="Shopping"),
        actions=[
            ToolAction(
                tool="list_tool",
                params={"operation": "create_list", "name": "Shopping"},
            ),
        ],
    )

    results = await execute_plan_actions(
        plan=plan,
        chat_id="test_chat",
        user_id="test_user",
        auto_approve=True,
    )

    assert len(results) == 1
    assert results[0].status == ToolStatus.SUCCESS
    assert "list_id" in results[0].data


def test_format_results_summary_success():
    """Test formatting successful results."""
    from uuid import uuid4

    from app.contracts.tools import ToolResult

    results = [
        ToolResult(
            call_id=uuid4(),
            tool_name="task_tool",
            status=ToolStatus.SUCCESS,
            data={"task_id": "123"},
            duration_ms=10.0,
        ),
    ]

    summary = format_results_summary(results)

    assert "✅" in summary
    assert "1 action(s) completed successfully" in summary


def test_format_results_summary_failed():
    """Test formatting failed results."""
    from uuid import uuid4

    from app.contracts.tools import ToolResult

    results = [
        ToolResult(
            call_id=uuid4(),
            tool_name="task_tool",
            status=ToolStatus.ERROR,
            error="Task not found",
            duration_ms=5.0,
        ),
    ]

    summary = format_results_summary(results)

    assert "❌" in summary
    assert "1 action(s) failed" in summary
    assert "Task not found" in summary


def test_format_results_summary_mixed():
    """Test formatting mixed success/failure results."""
    from uuid import uuid4

    from app.contracts.tools import ToolResult

    results = [
        ToolResult(
            call_id=uuid4(),
            tool_name="task_tool",
            status=ToolStatus.SUCCESS,
            data={"id": "1"},
            duration_ms=10.0,
        ),
        ToolResult(
            call_id=uuid4(),
            tool_name="task_tool",
            status=ToolStatus.ERROR,
            error="Failed",
            duration_ms=5.0,
        ),
    ]

    summary = format_results_summary(results)

    assert "✅" in summary
    assert "1 action(s) completed successfully" in summary
    assert "❌" in summary
    assert "1 action(s) failed" in summary


def test_update_plan_with_answers():
    """Test updating a plan with clarification answers."""
    plan = Plan(
        intent=IntentType.TASK_CREATE,
        entities=PlanEntities(title="Review PR"),
    )

    answers = {
        "priority": "2",
        "due_at": "2025-10-17T15:00:00",
    }

    updated_plan = update_plan_with_answers(plan, answers)

    assert updated_plan.entities.priority == 2
    assert updated_plan.entities.due_at == "2025-10-17T15:00:00"
    assert len(updated_plan.followups) == 0


def test_update_plan_with_items():
    """Test updating a plan with list items."""
    plan = Plan(
        intent=IntentType.LIST_ADD,
        entities=PlanEntities(list_name="Shopping"),
    )

    answers = {
        "items": "milk, bread, eggs",
    }

    updated_plan = update_plan_with_answers(plan, answers)

    assert len(updated_plan.entities.items) == 3
    assert "milk" in updated_plan.entities.items
    assert "bread" in updated_plan.entities.items
    assert "eggs" in updated_plan.entities.items


@pytest.mark.asyncio
async def test_capture_crew_e2e_task(capture_crew, capture_context, test_data_dir):
    """Test end-to-end capture flow for task creation."""
    # Note: This is a simplified test since we can't run actual LLM calls
    # In a real scenario, we'd mock the LLM or use a test LLM

    # For now, test that the crew can be instantiated and basic flow works
    assert capture_crew.memory_service is not None
    assert capture_context.chat_id == "test_chat"
    assert capture_context.auto_approve is True


@pytest.mark.asyncio
async def test_capture_crew_saves_to_memory(capture_crew, capture_context):
    """Test that capture crew saves interactions to memory."""
    from uuid import uuid4

    from app.contracts.tools import ToolResult

    # Simulate a successful capture
    user_input = "Create a task to review PR"
    plan = Plan(intent=IntentType.TASK_CREATE)
    results = [
        ToolResult(
            call_id=uuid4(),
            tool_name="task_tool",
            status=ToolStatus.SUCCESS,
            data={"task_id": "123"},
            duration_ms=10.0,
        ),
    ]

    # Save to memory
    await capture_crew._save_to_memory(user_input, plan, results, capture_context)

    # Verify saved to STM
    history = capture_crew.memory_service.stm.get_history(
        chat_id=capture_context.chat_id
    )

    assert len(history) == 2  # User message + assistant response
    assert history[0].role == "user"
    assert history[0].content == user_input
    assert history[1].role == "assistant"


@pytest.mark.asyncio
async def test_capture_crew_gets_context(capture_crew, capture_context):
    """Test that capture crew retrieves conversation context."""
    # Add some messages to STM
    capture_crew.memory_service.stm.add_message(
        chat_id=capture_context.chat_id,
        role="user",
        content="Hello",
    )
    capture_crew.memory_service.stm.add_message(
        chat_id=capture_context.chat_id,
        role="assistant",
        content="Hi there!",
    )

    # Get context
    context = await capture_crew._get_conversation_context(capture_context.chat_id)

    assert len(context) == 2
    assert context[0]["role"] == "user"
    assert context[0]["content"] == "Hello"
    assert context[1]["role"] == "assistant"
