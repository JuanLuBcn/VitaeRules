"""Main entry point for VitaeRules application."""

import asyncio
import sys

from .config import get_settings
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

    # TODO: Initialize and start Telegram bot adapter
    tracer.info("VitaeRules is ready!")
    tracer.info("Press Ctrl+C to stop")

    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
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
