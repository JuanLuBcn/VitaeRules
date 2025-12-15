"""Structured tracing and logging for observability."""

import json
import logging
import sys
import uuid
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .config import get_settings


class TraceEvent(str, Enum):
    """Event types for structured tracing."""

    # Planning events
    PLAN_START = "plan.start"
    PLAN_END = "plan.end"

    # Clarification events
    CLARIFIER_ASK = "clarifier.ask"
    CLARIFIER_ANSWER = "clarifier.answer"

    # Tool events
    TOOL_EXECUTE_START = "tool.execute.start"
    TOOL_EXECUTE_END = "tool.execute.end"
    TOOL_APPROVE = "tool.approve"
    TOOL_REJECT = "tool.reject"

    # Memory events
    MEMORY_WRITE = "memory.write"
    MEMORY_READ = "memory.read"

    # Retrieval events
    RETRIEVAL_QUERY = "retrieval.query"
    RETRIEVAL_RESULTS = "retrieval.results"
    RETRIEVAL_ANSWER = "retrieval.answer"

    # Diary events
    DIARY_START = "diary.start"
    DIARY_END = "diary.end"

    # System events
    APP_START = "app.start"
    APP_STOP = "app.stop"
    ERROR = "error"


class Tracer:
    """Structured event tracer with JSONL output."""

    def __init__(self, trace_file: Path | None = None, level: str = "info"):
        self.settings = get_settings()
        self.trace_file = trace_file or self.settings.trace_file
        self.level = level.upper()
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure logging with both console and file handlers."""
        # Console logger
        self.logger = logging.getLogger("vitaerules")
        self.logger.setLevel(self.level)
        self.logger.handlers.clear()

        # Console handler (pretty format)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.level)
        console_format = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(console_format)
        self.logger.addHandler(console_handler)

        # File handler (detailed logs to file for debugging)
        try:
            log_dir = Path("/app/data/logs")
            log_dir.mkdir(parents=True, exist_ok=True)
            log_file = log_dir / "vitae_app.log"
            
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(self.level)
            file_format = logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_format)
            self.logger.addHandler(file_handler)
            self.logger.info(f"File logging enabled: {log_file}")
        except Exception as e:
            self.logger.warning(f"Could not set up file logging: {e}")

    def trace(
        self,
        event: TraceEvent,
        *,
        chat_id: str | int | None = None,
        user_id: str | int | None = None,
        correlation_id: str | None = None,
        seq: int | None = None,
        duration_ms: float | None = None,
        ok: bool = True,
        error: str | None = None,
        preview: str | None = None,
        **extra: Any,
    ) -> None:
        """Write a structured trace event to JSONL file."""
        trace_record = {
            "ts": datetime.now(UTC).isoformat(),
            "env": self.settings.app_env,
            "event": event.value,
            "chat_id": str(chat_id) if chat_id is not None else None,
            "user_id": str(user_id) if user_id is not None else None,
            "correlation_id": correlation_id,
            "seq": seq,
            "dur_ms": duration_ms,
            "ok": ok,
            "error": error,
            "preview": preview,
            **extra,
        }

        # Remove None values for cleaner logs
        trace_record = {k: v for k, v in trace_record.items() if v is not None}

        # Write to JSONL file
        try:
            with open(self.trace_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(trace_record, ensure_ascii=False) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to write trace: {e}")

    def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message."""
        self.logger.info(message, extra=kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message."""
        self.logger.debug(message, extra=kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message."""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """Log an error message."""
        self.logger.error(message, extra=kwargs)

    def exception(self, message: str, **kwargs: Any) -> None:
        """Log an exception with traceback."""
        self.logger.exception(message, extra=kwargs)

    @staticmethod
    def generate_correlation_id() -> str:
        """Generate a unique correlation ID for tracing."""
        return str(uuid.uuid4())


# Global tracer instance
_tracer: Tracer | None = None


def get_tracer() -> Tracer:
    """Get or create the global tracer instance."""
    global _tracer
    if _tracer is None:
        settings = get_settings()
        _tracer = Tracer(level=settings.trace_level)
    return _tracer


def reload_tracer() -> Tracer:
    """Reload tracer (useful for testing)."""
    global _tracer
    settings = get_settings()
    _tracer = Tracer(level=settings.trace_level)
    return _tracer
