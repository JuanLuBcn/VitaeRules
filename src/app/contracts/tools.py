"""Tool contracts and base classes for CrewAI integration."""

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ToolStatus(str, Enum):
    """Tool execution status."""

    PENDING = "pending"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"


class ToolCall(BaseModel):
    """
    Request to execute a tool.

    Includes idempotency key for safe retries.
    """

    id: UUID = Field(default_factory=uuid4, description="Unique call identifier")
    tool_name: str = Field(description="Name of the tool to invoke")
    arguments: dict[str, Any] = Field(
        default_factory=dict, description="Tool arguments"
    )
    idempotency_key: str | None = Field(
        default=None,
        description="Optional key for idempotent operations",
    )
    correlation_id: str | None = Field(
        default=None,
        description="Correlation ID for tracing",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the call was created",
    )

    model_config = {"use_enum_values": True}


class ToolResult(BaseModel):
    """
    Result from tool execution.

    Contains both success/error status and structured data.
    """

    call_id: UUID = Field(description="ID of the originating ToolCall")
    tool_name: str = Field(description="Name of the executed tool")
    status: ToolStatus = Field(description="Execution status")
    data: dict[str, Any] | None = Field(
        default=None,
        description="Structured result data on success",
    )
    error: str | None = Field(
        default=None,
        description="Error message on failure",
    )
    duration_ms: float | None = Field(
        default=None,
        description="Execution time in milliseconds",
    )
    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When execution completed",
    )

    model_config = {"use_enum_values": True}

    def is_success(self) -> bool:
        """Check if the tool executed successfully."""
        return self.status == ToolStatus.SUCCESS

    def is_error(self) -> bool:
        """Check if the tool execution failed."""
        return self.status == ToolStatus.ERROR


class BaseTool(ABC):
    """
    Abstract base class for all tools.

    Tools should inherit from this and implement:
    - name: Unique identifier for the tool
    - description: What the tool does
    - schema: JSON Schema for arguments validation
    - execute: Core logic
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name (used for routing)."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""
        pass

    @property
    def schema(self) -> dict[str, Any]:
        """
        JSON Schema for tool arguments.

        Override to provide custom validation schema.
        """
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    @abstractmethod
    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the tool with validated arguments.

        Args:
            arguments: Validated tool arguments

        Returns:
            Result dictionary with tool-specific data

        Raises:
            Exception: On execution failure
        """
        pass

    def validate_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Validate arguments against the tool's schema.

        Args:
            arguments: Arguments to validate

        Returns:
            Validated arguments (potentially with defaults filled)

        Raises:
            ValueError: If validation fails
        """
        # For now, just return arguments as-is
        # Can be enhanced with jsonschema validation later
        return arguments

    async def __call__(self, call: ToolCall) -> ToolResult:
        """
        Execute the tool from a ToolCall and return a ToolResult.

        Handles validation, execution, timing, and error wrapping.

        Args:
            call: Tool call to execute

        Returns:
            Tool result with status and data/error
        """
        start_time = datetime.now(UTC)

        try:
            # Validate arguments
            validated_args = self.validate_arguments(call.arguments)

            # Execute tool
            result_data = await self.execute(validated_args)

            # Calculate duration
            duration_ms = (
                datetime.now(UTC) - start_time
            ).total_seconds() * 1000

            return ToolResult(
                call_id=call.id,
                tool_name=self.name,
                status=ToolStatus.SUCCESS,
                data=result_data,
                duration_ms=duration_ms,
            )

        except Exception as e:
            # Calculate duration even on error
            duration_ms = (
                datetime.now(UTC) - start_time
            ).total_seconds() * 1000

            return ToolResult(
                call_id=call.id,
                tool_name=self.name,
                status=ToolStatus.ERROR,
                error=str(e),
                duration_ms=duration_ms,
            )
