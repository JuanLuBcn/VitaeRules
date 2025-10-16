"""Tests for TaskTool."""

from datetime import UTC, datetime, timedelta

import pytest

from app.tools.task_tool import TaskTool


@pytest.fixture
def task_tool(test_data_dir, request):
    """Create a TaskTool instance for testing."""
    test_name = request.node.name
    db_path = test_data_dir / f"{test_name}_tasks.sqlite"
    return TaskTool(db_path=db_path)


@pytest.mark.asyncio
async def test_create_task(task_tool):
    """Test creating a new task."""
    result = await task_tool.execute({
        "operation": "create_task",
        "title": "Buy groceries",
        "user_id": "user1",
    })

    assert result["title"] == "Buy groceries"
    assert "task_id" in result
    assert "created_at" in result


@pytest.mark.asyncio
async def test_create_task_with_details(task_tool):
    """Test creating a task with full details."""
    due_date = (datetime.now(UTC) + timedelta(days=1)).isoformat()

    result = await task_tool.execute({
        "operation": "create_task",
        "title": "Important task",
        "description": "This is a detailed task",
        "due_at": due_date,
        "priority": 2,
        "user_id": "user1",
    })

    assert result["title"] == "Important task"
    assert result["description"] == "This is a detailed task"
    assert result["due_at"] == due_date
    assert result["priority"] == 2


@pytest.mark.asyncio
async def test_create_task_without_title(task_tool):
    """Test creating a task without a title fails."""
    with pytest.raises(ValueError, match="title is required"):
        await task_tool.execute({
            "operation": "create_task",
        })


@pytest.mark.asyncio
async def test_complete_task(task_tool):
    """Test marking a task as complete."""
    # Create task
    task_result = await task_tool.execute({
        "operation": "create_task",
        "title": "Task to complete",
    })
    task_id = task_result["task_id"]

    # Complete the task
    complete_result = await task_tool.execute({
        "operation": "complete_task",
        "task_id": task_id,
    })

    assert complete_result["completed"] is True
    assert complete_result["task_id"] == task_id
    assert "completed_at" in complete_result


@pytest.mark.asyncio
async def test_list_tasks(task_tool):
    """Test listing all tasks."""
    # Create multiple tasks
    await task_tool.execute({
        "operation": "create_task",
        "title": "Task 1",
        "user_id": "user1",
    })
    await task_tool.execute({
        "operation": "create_task",
        "title": "Task 2",
        "user_id": "user1",
    })

    # List tasks
    result = await task_tool.execute({
        "operation": "list_tasks",
        "user_id": "user1",
    })

    assert result["count"] == 2
    assert len(result["tasks"]) == 2


@pytest.mark.asyncio
async def test_list_tasks_filter_completed(task_tool):
    """Test filtering tasks by completion status."""
    # Create and complete one task
    task1 = await task_tool.execute({
        "operation": "create_task",
        "title": "Completed task",
        "user_id": "user1",
    })
    await task_tool.execute({
        "operation": "complete_task",
        "task_id": task1["task_id"],
    })

    # Create incomplete task
    await task_tool.execute({
        "operation": "create_task",
        "title": "Pending task",
        "user_id": "user1",
    })

    # List only incomplete tasks
    result = await task_tool.execute({
        "operation": "list_tasks",
        "user_id": "user1",
        "completed": False,
    })

    assert result["count"] == 1
    assert result["tasks"][0]["title"] == "Pending task"

    # List only completed tasks
    result_completed = await task_tool.execute({
        "operation": "list_tasks",
        "user_id": "user1",
        "completed": True,
    })

    assert result_completed["count"] == 1
    assert result_completed["tasks"][0]["title"] == "Completed task"


@pytest.mark.asyncio
async def test_update_task(task_tool):
    """Test updating task details."""
    # Create task
    task_result = await task_tool.execute({
        "operation": "create_task",
        "title": "Original title",
        "priority": 0,
    })
    task_id = task_result["task_id"]

    # Update task
    update_result = await task_tool.execute({
        "operation": "update_task",
        "task_id": task_id,
        "title": "Updated title",
        "description": "New description",
        "priority": 3,
    })

    assert update_result["updated"] is True
    assert update_result["task_id"] == task_id

    # Verify updates
    tasks = await task_tool.execute({
        "operation": "list_tasks",
    })
    task = tasks["tasks"][0]
    assert task["title"] == "Updated title"
    assert task["description"] == "New description"
    assert task["priority"] == 3


@pytest.mark.asyncio
async def test_update_nonexistent_task(task_tool):
    """Test updating a task that doesn't exist."""
    with pytest.raises(ValueError, match="Task not found"):
        await task_tool.execute({
            "operation": "update_task",
            "task_id": "nonexistent-id",
            "title": "New title",
        })


@pytest.mark.asyncio
async def test_update_task_without_fields(task_tool):
    """Test updating a task without any fields fails."""
    task_result = await task_tool.execute({
        "operation": "create_task",
        "title": "Test task",
    })
    task_id = task_result["task_id"]

    with pytest.raises(ValueError, match="No fields to update"):
        await task_tool.execute({
            "operation": "update_task",
            "task_id": task_id,
        })


@pytest.mark.asyncio
async def test_delete_task(task_tool):
    """Test deleting a task."""
    # Create task
    task_result = await task_tool.execute({
        "operation": "create_task",
        "title": "To be deleted",
    })
    task_id = task_result["task_id"]

    # Delete task
    delete_result = await task_tool.execute({
        "operation": "delete_task",
        "task_id": task_id,
    })

    assert delete_result["deleted"] is True
    assert delete_result["task_id"] == task_id

    # Verify it's gone
    tasks = await task_tool.execute({
        "operation": "list_tasks",
    })
    assert tasks["count"] == 0


@pytest.mark.asyncio
async def test_task_priority_ordering(task_tool):
    """Test that tasks are ordered by priority."""
    # Create tasks with different priorities
    await task_tool.execute({
        "operation": "create_task",
        "title": "Low priority",
        "priority": 0,
    })
    await task_tool.execute({
        "operation": "create_task",
        "title": "High priority",
        "priority": 3,
    })
    await task_tool.execute({
        "operation": "create_task",
        "title": "Medium priority",
        "priority": 1,
    })

    # List tasks (should be ordered by priority desc)
    result = await task_tool.execute({
        "operation": "list_tasks",
    })

    tasks = result["tasks"]
    assert tasks[0]["title"] == "High priority"
    assert tasks[1]["title"] == "Medium priority"
    assert tasks[2]["title"] == "Low priority"


@pytest.mark.asyncio
async def test_tool_metadata(task_tool):
    """Test TaskTool metadata."""
    assert task_tool.name == "task_tool"
    assert "task" in task_tool.description.lower()

    schema = task_tool.schema
    assert "operation" in schema["properties"]
    operations = schema["properties"]["operation"]["enum"]
    assert "create_task" in operations
    assert "complete_task" in operations
    assert "list_tasks" in operations
