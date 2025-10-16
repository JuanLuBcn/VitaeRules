"""Tests for tool registry."""

import pytest

from app.contracts import BaseTool, ToolCall, ToolStatus
from app.tools.registry import ToolRegistry


class SimpleTestTool(BaseTool):
    """Simple test tool."""

    @property
    def name(self) -> str:
        return "simple_tool"

    @property
    def description(self) -> str:
        return "A simple test tool"

    async def execute(self, arguments: dict) -> dict:
        return {"executed": True, "args": arguments}


class FailingTestTool(BaseTool):
    """Test tool that fails."""

    @property
    def name(self) -> str:
        return "failing_tool"

    @property
    def description(self) -> str:
        return "A tool that fails"

    async def execute(self, arguments: dict) -> dict:
        raise ValueError("Intentional failure")


def test_registry_initialization():
    """Test registry initialization."""
    registry = ToolRegistry()
    assert registry is not None
    assert len(registry.list_tools()) == 0


def test_register_tool():
    """Test registering a tool."""
    registry = ToolRegistry()
    tool = SimpleTestTool()

    registry.register(tool)

    assert registry.get("simple_tool") == tool
    assert len(registry.list_tools()) == 1


def test_register_duplicate_tool():
    """Test registering duplicate tool fails."""
    registry = ToolRegistry()
    tool1 = SimpleTestTool()
    tool2 = SimpleTestTool()

    registry.register(tool1)

    with pytest.raises(ValueError, match="already registered"):
        registry.register(tool2)


def test_unregister_tool():
    """Test unregistering a tool."""
    registry = ToolRegistry()
    tool = SimpleTestTool()

    registry.register(tool)
    assert registry.get("simple_tool") is not None

    registry.unregister("simple_tool")
    assert registry.get("simple_tool") is None


def test_get_nonexistent_tool():
    """Test getting a tool that doesn't exist."""
    registry = ToolRegistry()

    tool = registry.get("nonexistent")
    assert tool is None


def test_list_tools():
    """Test listing all registered tools."""
    registry = ToolRegistry()
    tool1 = SimpleTestTool()

    class AnotherTool(BaseTool):
        @property
        def name(self) -> str:
            return "another_tool"

        @property
        def description(self) -> str:
            return "Another test tool"

        async def execute(self, arguments: dict) -> dict:
            return {}

    tool2 = AnotherTool()

    registry.register(tool1)
    registry.register(tool2)

    tools = registry.list_tools()
    assert len(tools) == 2

    tool_names = [t["name"] for t in tools]
    assert "simple_tool" in tool_names
    assert "another_tool" in tool_names


@pytest.mark.asyncio
async def test_execute_tool():
    """Test executing a tool via registry."""
    registry = ToolRegistry()
    tool = SimpleTestTool()
    registry.register(tool)

    call = ToolCall(
        tool_name="simple_tool",
        arguments={"test": "value"},
    )

    result = await registry.execute(call)

    assert result.status == ToolStatus.SUCCESS
    assert result.data["executed"] is True
    assert result.data["args"]["test"] == "value"


@pytest.mark.asyncio
async def test_execute_nonexistent_tool():
    """Test executing a tool that doesn't exist."""
    registry = ToolRegistry()

    call = ToolCall(
        tool_name="nonexistent",
        arguments={},
    )

    result = await registry.execute(call)

    assert result.status == ToolStatus.ERROR
    assert "not found" in result.error


@pytest.mark.asyncio
async def test_execute_failing_tool():
    """Test executing a tool that fails."""
    registry = ToolRegistry()
    tool = FailingTestTool()
    registry.register(tool)

    call = ToolCall(
        tool_name="failing_tool",
        arguments={},
    )

    result = await registry.execute(call)

    assert result.status == ToolStatus.ERROR
    assert "Intentional failure" in result.error


@pytest.mark.asyncio
async def test_idempotency_cache():
    """Test idempotency caching."""
    registry = ToolRegistry()
    tool = SimpleTestTool()
    registry.register(tool)

    call1 = ToolCall(
        tool_name="simple_tool",
        arguments={"test": "value"},
        idempotency_key="test-key-1",
    )

    # First execution
    result1 = await registry.execute(call1)
    assert result1.status == ToolStatus.SUCCESS

    # Second execution with same key should return cached result
    call2 = ToolCall(
        tool_name="simple_tool",
        arguments={"test": "different"},
        idempotency_key="test-key-1",
    )

    result2 = await registry.execute(call2)
    assert result2.status == ToolStatus.SUCCESS
    assert result2.call_id == result1.call_id  # Same result
    assert result2.data == result1.data


@pytest.mark.asyncio
async def test_idempotency_cache_no_key():
    """Test execution without idempotency key."""
    registry = ToolRegistry()
    tool = SimpleTestTool()
    registry.register(tool)

    call1 = ToolCall(
        tool_name="simple_tool",
        arguments={"test": "value"},
    )

    call2 = ToolCall(
        tool_name="simple_tool",
        arguments={"test": "value"},
    )

    result1 = await registry.execute(call1)
    result2 = await registry.execute(call2)

    # Different executions, different call IDs
    assert result1.call_id != result2.call_id


@pytest.mark.asyncio
async def test_execute_batch():
    """Test executing multiple tools in batch."""
    registry = ToolRegistry()
    tool = SimpleTestTool()
    registry.register(tool)

    calls = [
        ToolCall(tool_name="simple_tool", arguments={"num": 1}),
        ToolCall(tool_name="simple_tool", arguments={"num": 2}),
        ToolCall(tool_name="simple_tool", arguments={"num": 3}),
    ]

    results = await registry.execute_batch(calls)

    assert len(results) == 3
    assert all(r.status == ToolStatus.SUCCESS for r in results)
    assert results[0].data["args"]["num"] == 1
    assert results[1].data["args"]["num"] == 2
    assert results[2].data["args"]["num"] == 3


@pytest.mark.asyncio
async def test_execute_batch_with_errors():
    """Test batch execution with some failures."""
    registry = ToolRegistry()
    simple_tool = SimpleTestTool()
    failing_tool = FailingTestTool()

    registry.register(simple_tool)
    registry.register(failing_tool)

    calls = [
        ToolCall(tool_name="simple_tool", arguments={}),
        ToolCall(tool_name="failing_tool", arguments={}),
        ToolCall(tool_name="simple_tool", arguments={}),
    ]

    results = await registry.execute_batch(calls)

    assert len(results) == 3
    assert results[0].status == ToolStatus.SUCCESS
    assert results[1].status == ToolStatus.ERROR
    assert results[2].status == ToolStatus.SUCCESS


def test_clear_idempotency_cache():
    """Test clearing the idempotency cache."""
    registry = ToolRegistry()
    tool = SimpleTestTool()
    registry.register(tool)

    # Add something to cache
    registry._idempotency_cache["test-key"] = None

    assert len(registry._idempotency_cache) > 0

    registry.clear_idempotency_cache()
    assert len(registry._idempotency_cache) == 0
