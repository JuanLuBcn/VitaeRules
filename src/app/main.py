"""Main entry point for VitaeRules application."""

import asyncio
import logging
import sys

from .adapters.telegram import VitaeBot
from .config import get_settings
from .llm import get_llm_service
from .memory import MemoryService
from .tools.registry import get_registry
from .tools.list_tool import ListTool
from .tools.task_tool import TaskTool
from .tools.temporal_tool import TemporalTool
from .tools.memory_note_tool import MemoryNoteTool
from .tracing import TraceEvent, get_tracer


def configure_logging():
    """Configure logging to reduce noise."""
    # Suppress verbose library logs
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("langchain").setLevel(logging.WARNING)


async def main_async() -> None:
    """Async main function."""
    configure_logging()
    
    settings = get_settings()
    tracer = get_tracer()

    print("\n🚀 Starting VitaeRules Telegram Bot...")
    print("="*80)
    
    # Initialize services
    print("⚙️  Initializing services...")
    
    # Create memory service
    memory_service = MemoryService()
    
    # Create LLM service
    llm_service = get_llm_service()
    print(f"✓ LLM Service: {settings.llm_backend} ({settings.ollama_model})")
    
    # Get global tool registry and register tools
    tool_registry = get_registry()
    tool_registry.register(TaskTool())
    tool_registry.register(ListTool())
    tool_registry.register(TemporalTool())
    tool_registry.register(MemoryNoteTool(memory_service=memory_service))
    print(f"✓ Tools registered: {len(tool_registry.list_tools())}")
    
    # Create and start Telegram bot
    print(f"✓ Memory Service: Connected")
    print("="*80)
    print("✅ Bot is ready! Waiting for messages...")
    print("="*80)
    
    bot = VitaeBot(
        settings=settings,
        memory_service=memory_service,
        tool_registry=tool_registry,
        llm_service=llm_service,
    )

    try:
        await bot.run()
    except KeyboardInterrupt:
        print("\n\n" + "="*80)
        print("👋 Shutting down gracefully...")
        print("="*80 + "\n")
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
