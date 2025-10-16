"""Tests for tool contracts."""

from datetime import datetime

import pytest

from app.contracts import BaseTool, ToolCall, ToolResult, ToolStatus


class MockTool(BaseTool):
    """Mock tool for testing."""

    @property
    def name(self) -> str:
        return "mock_tool"

    @property
    def description(self) -> str:
        return "A mock tool for testing"

    @property
    def schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "value": {"type": "string"},
            },
            "required": ["value"],
        }

    async def execute(self, arguments: dict) -> dict:
        """Return the value argument."""
        return {"result": arguments.get("value", "")}


class ErrorTool(BaseTool):
    """Tool that always raises an error."""

    @property
    def name(self) -> str:
        return "error_tool"

    @property
    def description(self) -> str:
        return "A tool that raises errors"

    async def execute(self, arguments: dict) -> dict:
        """Always raise an error."""
        raise ValueError("This tool always fails")


def test_tool_call_creation():
    """Test creating a tool call."""
    call = ToolCall(
        tool_name="test_tool",
        arguments={"key": "value"},
        idempotency_key="test-key",
    )

    assert call.tool_name == "test_tool"
    assert call.arguments == {"key": "value"}
    assert call.idempotency_key == "test-key"
    assert call.id is not None
    assert isinstance(call.created_at, datetime)


def test_tool_result_success():
    """Test creating a successful tool result."""
    from uuid import uuid4

    call_id = uuid4()
    result = ToolResult(
        call_id=call_id,
        tool_name="test_tool",
        status=ToolStatus.SUCCESS,
        data={"result": "success"},
        duration_ms=100.5,
    )

    assert result.call_id == call_id
    assert result.tool_name == "test_tool"
    assert result.status == ToolStatus.SUCCESS
    assert result.data == {"result": "success"}
    assert result.duration_ms == 100.5
    assert result.is_success()
    assert not result.is_error()


def test_tool_result_error():
    """Test creating an error tool result."""
    from uuid import uuid4

    call_id = uuid4()
    result = ToolResult(
        call_id=call_id,
        tool_name="test_tool",
        status=ToolStatus.ERROR,
        error="Something went wrong",
    )

    assert result.status == ToolStatus.ERROR
    assert result.error == "Something went wrong"
    assert result.is_error()
    assert not result.is_success()


@pytest.mark.asyncio
async def test_base_tool_execute_success():
    """Test executing a tool successfully."""
    tool = MockTool()
    call = ToolCall(
        tool_name="mock_tool",
        arguments={"value": "test"},
    )

    result = await tool(call)

    assert result.status == ToolStatus.SUCCESS
    assert result.data == {"result": "test"}
    assert result.duration_ms is not None
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_base_tool_execute_error():
    """Test tool execution with error."""
    tool = ErrorTool()
    call = ToolCall(
        tool_name="error_tool",
        arguments={},
    )

    result = await tool(call)

    assert result.status == ToolStatus.ERROR
    assert "always fails" in result.error
    assert result.duration_ms is not None


def test_tool_schema():
    """Test tool schema property."""
    tool = MockTool()

    schema = tool.schema
    assert schema["type"] == "object"
    assert "value" in schema["properties"]
    assert "value" in schema["required"]


def test_tool_metadata():
    """Test tool name and description."""
    tool = MockTool()

    assert tool.name == "mock_tool"
    assert tool.description == "A mock tool for testing"
