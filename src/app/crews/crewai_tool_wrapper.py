"""Wrapper to convert our BaseTool implementations to CrewAI-compatible tools.

This module provides utilities to wrap our custom BaseTool implementations
so they can be used with CrewAI agents.
"""

import asyncio
from typing import Any

from crewai import Tool

from app.contracts.tools import BaseTool
from app.tracing import get_tracer

logger = get_tracer()


def wrap_tool_for_crewai(base_tool: BaseTool) -> Tool:
    """Convert a BaseTool to a CrewAI Tool.
    
    Args:
        base_tool: Our BaseTool implementation
        
    Returns:
        CrewAI Tool that wraps the BaseTool
    """
    # CrewAI expects synchronous functions, but our tools are async
    # We need to create a sync wrapper that runs the async execute
    def sync_execute(arguments: dict[str, Any]) -> dict[str, Any]:
        """Synchronous wrapper for async tool execution."""
        try:
            # Run the async execute in a new event loop if needed
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No event loop running, create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # If we have a running loop, use asyncio.create_task
            # Otherwise, use loop.run_until_complete
            if loop.is_running():
                # We're in an async context, but CrewAI called us synchronously
                # This is tricky - we'll use run_coroutine_threadsafe
                import concurrent.futures
                import threading
                
                # Create a new thread with its own event loop
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(base_tool.execute(arguments))
                    finally:
                        new_loop.close()
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    return future.result()
            else:
                # No running loop, just run it
                return loop.run_until_complete(base_tool.execute(arguments))
                
        except Exception as e:
            logger.error(
                f"Error executing tool {base_tool.name}",
                extra={"error": str(e), "arguments": arguments}
            )
            return {
                "success": False,
                "error": str(e)
            }
    
    # Create the CrewAI Tool
    crewai_tool = Tool(
        name=base_tool.name,
        description=base_tool.description,
        func=sync_execute
    )
    
    logger.debug(f"Wrapped tool '{base_tool.name}' for CrewAI")
    
    return crewai_tool


def wrap_tools_for_crewai(base_tools: list[BaseTool]) -> list[Tool]:
    """Convert a list of BaseTools to CrewAI Tools.
    
    Args:
        base_tools: List of our BaseTool implementations
        
    Returns:
        List of CrewAI Tools
    """
    return [wrap_tool_for_crewai(tool) for tool in base_tools]
