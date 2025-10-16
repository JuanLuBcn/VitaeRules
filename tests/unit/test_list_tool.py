"""Tests for ListTool."""

import pytest

from app.tools.list_tool import ListTool


@pytest.fixture
def list_tool(test_data_dir, request):
    """Create a ListTool instance for testing."""
    test_name = request.node.name
    db_path = test_data_dir / f"{test_name}_lists.sqlite"
    return ListTool(db_path=db_path)


@pytest.mark.asyncio
async def test_create_list(list_tool):
    """Test creating a new list."""
    result = await list_tool.execute({
        "operation": "create_list",
        "list_name": "Shopping",
        "user_id": "user1",
    })

    assert result["list_name"] == "Shopping"
    assert "list_id" in result
    assert "created_at" in result


@pytest.mark.asyncio
async def test_create_list_without_name(list_tool):
    """Test creating a list without a name fails."""
    with pytest.raises(ValueError, match="list_name is required"):
        await list_tool.execute({
            "operation": "create_list",
        })


@pytest.mark.asyncio
async def test_add_item_to_list(list_tool):
    """Test adding an item to a list."""
    # Create list first
    list_result = await list_tool.execute({
        "operation": "create_list",
        "list_name": "Groceries",
    })
    list_id = list_result["list_id"]

    # Add item
    item_result = await list_tool.execute({
        "operation": "add_item",
        "list_id": list_id,
        "item_text": "Milk",
    })

    assert item_result["item_text"] == "Milk"
    assert item_result["list_id"] == list_id
    assert "item_id" in item_result
    assert item_result["position"] == 1


@pytest.mark.asyncio
async def test_add_multiple_items(list_tool):
    """Test adding multiple items maintains position."""
    list_result = await list_tool.execute({
        "operation": "create_list",
        "list_name": "Tasks",
    })
    list_id = list_result["list_id"]

    # Add three items
    item1 = await list_tool.execute({
        "operation": "add_item",
        "list_id": list_id,
        "item_text": "First",
    })
    item2 = await list_tool.execute({
        "operation": "add_item",
        "list_id": list_id,
        "item_text": "Second",
    })
    item3 = await list_tool.execute({
        "operation": "add_item",
        "list_id": list_id,
        "item_text": "Third",
    })

    assert item1["position"] == 1
    assert item2["position"] == 2
    assert item3["position"] == 3


@pytest.mark.asyncio
async def test_list_items(list_tool):
    """Test listing items in a list."""
    list_result = await list_tool.execute({
        "operation": "create_list",
        "list_name": "Notes",
    })
    list_id = list_result["list_id"]

    # Add items
    await list_tool.execute({
        "operation": "add_item",
        "list_id": list_id,
        "item_text": "Item 1",
    })
    await list_tool.execute({
        "operation": "add_item",
        "list_id": list_id,
        "item_text": "Item 2",
    })

    # List items
    result = await list_tool.execute({
        "operation": "list_items",
        "list_id": list_id,
    })

    assert result["count"] == 2
    assert len(result["items"]) == 2
    assert result["items"][0]["text"] == "Item 1"
    assert result["items"][1]["text"] == "Item 2"


@pytest.mark.asyncio
async def test_complete_item(list_tool):
    """Test marking an item as complete."""
    list_result = await list_tool.execute({
        "operation": "create_list",
        "list_name": "Todo",
    })
    list_id = list_result["list_id"]

    item_result = await list_tool.execute({
        "operation": "add_item",
        "list_id": list_id,
        "item_text": "Task to complete",
    })
    item_id = item_result["item_id"]

    # Complete the item
    complete_result = await list_tool.execute({
        "operation": "complete_item",
        "item_id": item_id,
    })

    assert complete_result["completed"] is True
    assert complete_result["item_id"] == item_id
    assert "completed_at" in complete_result


@pytest.mark.asyncio
async def test_remove_item(list_tool):
    """Test removing an item from a list."""
    list_result = await list_tool.execute({
        "operation": "create_list",
        "list_name": "Temp",
    })
    list_id = list_result["list_id"]

    item_result = await list_tool.execute({
        "operation": "add_item",
        "list_id": list_id,
        "item_text": "To be removed",
    })
    item_id = item_result["item_id"]

    # Remove the item
    remove_result = await list_tool.execute({
        "operation": "remove_item",
        "item_id": item_id,
    })

    assert remove_result["removed"] is True
    assert remove_result["item_id"] == item_id

    # Verify it's gone
    list_items = await list_tool.execute({
        "operation": "list_items",
        "list_id": list_id,
    })
    assert list_items["count"] == 0


@pytest.mark.asyncio
async def test_delete_list(list_tool):
    """Test deleting a list."""
    list_result = await list_tool.execute({
        "operation": "create_list",
        "list_name": "To Delete",
    })
    list_id = list_result["list_id"]

    # Add an item
    await list_tool.execute({
        "operation": "add_item",
        "list_id": list_id,
        "item_text": "Item",
    })

    # Delete the list
    delete_result = await list_tool.execute({
        "operation": "delete_list",
        "list_id": list_id,
    })

    assert delete_result["deleted"] is True
    assert delete_result["list_id"] == list_id


@pytest.mark.asyncio
async def test_get_lists(list_tool):
    """Test getting all lists."""
    # Create multiple lists
    await list_tool.execute({
        "operation": "create_list",
        "list_name": "List 1",
        "user_id": "user1",
    })
    await list_tool.execute({
        "operation": "create_list",
        "list_name": "List 2",
        "user_id": "user1",
    })

    # Get all lists for user
    result = await list_tool.execute({
        "operation": "get_lists",
        "user_id": "user1",
    })

    assert result["count"] == 2
    assert len(result["lists"]) == 2

    list_names = [lst["name"] for lst in result["lists"]]
    assert "List 1" in list_names
    assert "List 2" in list_names


@pytest.mark.asyncio
async def test_resolve_list_by_name(list_tool):
    """Test resolving list by name instead of ID."""
    await list_tool.execute({
        "operation": "create_list",
        "list_name": "Named List",
    })

    # Add item using list name
    result = await list_tool.execute({
        "operation": "add_item",
        "list_name": "Named List",
        "item_text": "Item via name",
    })

    assert result["item_text"] == "Item via name"


@pytest.mark.asyncio
async def test_tool_schema(list_tool):
    """Test ListTool schema."""
    schema = list_tool.schema

    assert schema["type"] == "object"
    assert "operation" in schema["properties"]
    assert "operation" in schema["required"]

    operations = schema["properties"]["operation"]["enum"]
    assert "create_list" in operations
    assert "add_item" in operations
    assert "complete_item" in operations


@pytest.mark.asyncio
async def test_tool_metadata(list_tool):
    """Test ListTool metadata."""
    assert list_tool.name == "list_tool"
    assert "lists" in list_tool.description.lower()
