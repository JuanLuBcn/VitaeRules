"""Tests for tracing module."""

import json

from app.tracing import TraceEvent, Tracer, get_tracer


def test_tracer_initialization(test_data_dir):
    """Test that tracer initializes correctly."""
    trace_file = test_data_dir / "test_trace.jsonl"
    tracer = Tracer(trace_file=trace_file, level="debug")

    assert tracer.trace_file == trace_file
    assert tracer.level == "DEBUG"
    assert tracer.logger.name == "vitaerules"


def test_trace_event_writing(test_data_dir):
    """Test that trace events are written to JSONL file."""
    trace_file = test_data_dir / "test_trace.jsonl"
    tracer = Tracer(trace_file=trace_file)

    tracer.trace(
        TraceEvent.PLAN_START,
        chat_id="123",
        user_id="456",
        correlation_id="test-correlation",
        preview="Test event",
    )

    # Read the trace file
    assert trace_file.exists()
    with open(trace_file) as f:
        line = f.readline()
        event = json.loads(line)

    assert event["event"] == "plan.start"
    assert event["chat_id"] == "123"
    assert event["user_id"] == "456"
    assert event["correlation_id"] == "test-correlation"
    assert event["preview"] == "Test event"
    assert "ts" in event
    assert event["env"] == "test"


def test_trace_event_filters_none_values(test_data_dir):
    """Test that None values are filtered from trace events."""
    trace_file = test_data_dir / "test_trace_none.jsonl"  # Use unique file
    tracer = Tracer(trace_file=trace_file)

    tracer.trace(
        TraceEvent.MEMORY_WRITE,
        chat_id="123",
        user_id=None,  # Should be filtered
        error=None,  # Should be filtered
    )

    with open(trace_file) as f:
        event = json.loads(f.readline())

    assert "chat_id" in event
    assert "user_id" not in event
    assert "error" not in event


def test_trace_correlation_id_generation():
    """Test correlation ID generation."""
    correlation_id = Tracer.generate_correlation_id()

    assert isinstance(correlation_id, str)
    assert len(correlation_id) == 36  # UUID format
    assert correlation_id.count("-") == 4


def test_logger_methods(test_data_dir, caplog):
    """Test logger convenience methods."""
    trace_file = test_data_dir / "test_trace.jsonl"
    tracer = Tracer(trace_file=trace_file, level="debug")

    tracer.info("Info message")
    tracer.debug("Debug message")
    tracer.warning("Warning message")
    tracer.error("Error message")

    # Check that messages were logged
    assert "Info message" in caplog.text
    assert "Debug message" in caplog.text
    assert "Warning message" in caplog.text
    assert "Error message" in caplog.text


def test_get_tracer_singleton():
    """Test that get_tracer returns the same instance."""
    tracer1 = get_tracer()
    tracer2 = get_tracer()

    assert tracer1 is tracer2
