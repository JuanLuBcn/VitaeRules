"""Tool Registry for managing and executing tools."""

import asyncio
from typing import Any

from ..config import get_settings
from ..contracts import BaseTool, ToolCall, ToolResult, ToolStatus
from ..tracing import get_tracer


class ToolRegistry:
    """
    Registry for tool discovery, validation, and execution.

    Provides:
    - Tool registration and lookup by name
    - Idempotency handling for retried calls
    - Execution tracing and metrics
    """

    def __init__(self):
        """Initialize the tool registry."""
        self.settings = get_settings()
        self.tracer = get_tracer()

        self._tools: dict[str, BaseTool] = {}
        self._idempotency_cache: dict[str, ToolResult] = {}

        self.tracer.info("Tool registry initialized")

    def register(self, tool: BaseTool) -> None:
        """
        Register a tool.

        Args:
            tool: Tool instance to register

        Raises:
            ValueError: If tool name is already registered
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")

        self._tools[tool.name] = tool
        self.tracer.info(f"Registered tool: {tool.name}")

    def unregister(self, tool_name: str) -> None:
        """
        Unregister a tool.

        Args:
            tool_name: Name of tool to unregister
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            self.tracer.info(f"Unregistered tool: {tool_name}")

    def get(self, tool_name: str) -> BaseTool | None:
        """
        Get a registered tool by name.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_name)

    def list_tools(self) -> list[dict[str, Any]]:
        """
        List all registered tools with metadata.

        Returns:
            List of tool info dictionaries
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "schema": tool.schema,
            }
            for tool in self._tools.values()
        ]

    async def execute(self, call: ToolCall) -> ToolResult:
        """
        Execute a tool call with idempotency support.

        Args:
            call: Tool call to execute

        Returns:
            Tool result
        """
        # Check idempotency cache
        if call.idempotency_key:
            cached_result = self._idempotency_cache.get(call.idempotency_key)
            if cached_result:
                self.tracer.debug(
                    f"Tool call hit idempotency cache: key={call.idempotency_key}"
                )
                return cached_result

        # Get tool
        tool = self.get(call.tool_name)
        if not tool:
            self.tracer.error(f"Tool not found: {call.tool_name}")
            return ToolResult(
                call_id=call.id,
                tool_name=call.tool_name,
                status=ToolStatus.ERROR,
                error=f"Tool '{call.tool_name}' not found in registry",
            )

        # Execute tool
        self.tracer.debug(
            f"Executing tool: {call.tool_name}",
            tool=call.tool_name,
            call_id=str(call.id),
            correlation_id=call.correlation_id,
        )

        result = await tool(call)

        # Cache result if idempotency key provided
        if call.idempotency_key and result.is_success():
            self._idempotency_cache[call.idempotency_key] = result

        # Trace result
        if result.is_success():
            self.tracer.debug(
                f"Tool executed successfully: {call.tool_name}",
                tool=call.tool_name,
                duration_ms=result.duration_ms,
            )
        else:
            self.tracer.error(
                f"Tool execution failed: {call.tool_name}",
                tool=call.tool_name,
                error=result.error,
            )

        return result

    async def execute_batch(self, calls: list[ToolCall]) -> list[ToolResult]:
        """
        Execute multiple tool calls concurrently.

        Args:
            calls: List of tool calls to execute

        Returns:
            List of tool results in same order as calls
        """
        tasks = [self.execute(call) for call in calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    ToolResult(
                        call_id=calls[i].id,
                        tool_name=calls[i].tool_name,
                        status=ToolStatus.ERROR,
                        error=str(result),
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def clear_idempotency_cache(self) -> None:
        """Clear the idempotency cache (useful for testing)."""
        self._idempotency_cache.clear()
        self.tracer.debug("Idempotency cache cleared")


# Global registry singleton
_registry: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    """
    Get the global tool registry singleton.

    Returns:
        Tool registry instance
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def register_tool(tool: BaseTool) -> None:
    """
    Register a tool in the global registry.

    Args:
        tool: Tool to register
    """
    registry = get_registry()
    registry.register(tool)
