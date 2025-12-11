"""Utility to wrap our BaseTool implementations as CrewAI-compatible tools."""

from typing import Any, Callable
from crewai.tools import BaseTool as CrewAIBaseTool

from app.contracts.tools import BaseTool
from app.tracing import get_tracer

logger = get_tracer()


class CrewAIToolWrapper(CrewAIBaseTool):
    """
    Wraps our BaseTool implementation as a CrewAI-compatible tool.
    
    This adapter allows our custom tools (TaskTool, ListTool, etc.) to work
    seamlessly with CrewAI agents.
    """
    
    name: str
    description: str
    wrapped_tool: BaseTool
    
    def __init__(self, base_tool: BaseTool, **kwargs):
        """
        Initialize the wrapper.
        
        Args:
            base_tool: Our BaseTool implementation to wrap
        """
        super().__init__(
            name=base_tool.name,
            description=base_tool.description,
            wrapped_tool=base_tool,
            **kwargs
        )
    
    def _run(self, **kwargs) -> dict[str, Any]:
        """
        Synchronous execution (required by CrewAI BaseTool).
        
        Note: Our tools are async, so this raises an error if called directly.
        CrewAI should use _arun for async tools.
        """
        raise NotImplementedError(
            f"Tool {self.wrapped_tool.name} is async. Use _arun instead."
        )
    
    async def _arun(self, **kwargs) -> dict[str, Any]:
        """
        Asynchronous execution (called by CrewAI for async tools).
        
        Args:
            **kwargs: Tool arguments
            
        Returns:
            Tool execution result
        """
        try:
            # Validate arguments against schema
            validated_args = self.wrapped_tool.validate_arguments(kwargs)
            
            # Execute the tool
            result = await self.wrapped_tool.execute(validated_args)
            
            logger.info(
                f"Tool {self.wrapped_tool.name} executed successfully",
                extra={"tool": self.wrapped_tool.name, "args": kwargs}
            )
            
            return result
            
        except Exception as e:
            logger.error(
                f"Tool {self.wrapped_tool.name} execution failed",
                extra={"tool": self.wrapped_tool.name, "error": str(e)}
            )
            return {
                "success": False,
                "error": str(e),
                "tool": self.wrapped_tool.name
            }


def wrap_tool_for_crewai(base_tool: BaseTool) -> CrewAIBaseTool:
    """
    Wrap our BaseTool implementation as a CrewAI-compatible tool.
    
    Args:
        base_tool: Our BaseTool implementation (TaskTool, ListTool, etc.)
        
    Returns:
        CrewAI BaseTool object that can be passed to agents
    """
    return CrewAIToolWrapper(base_tool=base_tool)
