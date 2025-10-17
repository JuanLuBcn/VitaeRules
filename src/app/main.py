"""Main entry point for VitaeRules application."""

import asyncio
import sys

from .adapters.telegram import VitaeBot
from .config import get_settings
from .memory import MemoryService
from .tools.registry import ToolRegistry
from .tools.list_tool import ListTool
from .tools.task_tool import TaskTool
from .tools.temporal_tool import TemporalTool
from .tools.memory_note_tool import MemoryNoteTool
from .tracing import TraceEvent, get_tracer


async def main_async() -> None:
    """Async main function."""
    settings = get_settings()
    tracer = get_tracer()

    tracer.info("Starting VitaeRules...")
    tracer.trace(
        TraceEvent.APP_START,
        env=settings.app_env,
        llm_backend=settings.llm_backend,
        vector_backend=settings.vector_backend,
    )

    # Initialize services
    tracer.info("Initializing services...")
    
    # Create memory service
    memory_service = MemoryService()
    
    # Create tool registry and register tools
    tool_registry = ToolRegistry()
    tool_registry.register(TaskTool())
    tool_registry.register(ListTool())
    tool_registry.register(TemporalTool())
    tool_registry.register(MemoryNoteTool(memory_service=memory_service))
    
    tracer.info("Services initialized", extra={"tools": len(tool_registry.list_tools())})
    
    # Create and start Telegram bot
    tracer.info("Starting Telegram bot...")
    bot = VitaeBot(
        settings=settings,
        memory_service=memory_service,
        tool_registry=tool_registry,
    )
    
    tracer.info("VitaeRules is ready!")
    tracer.info("Telegram bot is running. Press Ctrl+C to stop")

    try:
        await bot.run()
    except KeyboardInterrupt:
        tracer.info("Shutting down...")
        tracer.trace(TraceEvent.APP_STOP)


def main() -> None:
    """Entry point for the application."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        tracer = get_tracer()
        tracer.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
