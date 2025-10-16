"""Tests for TemporalTool."""

from datetime import UTC, datetime, timedelta

import pytest

from app.tools.temporal_tool import TemporalTool


@pytest.fixture
def temporal_tool():
    """Create a TemporalTool instance for testing."""
    return TemporalTool()


@pytest.mark.asyncio
async def test_parse_datetime_tomorrow(temporal_tool):
    """Test parsing 'tomorrow at 3pm'."""
    result = await temporal_tool.execute({
        "operation": "parse_datetime",
        "text": "tomorrow at 3pm",
    })

    parsed_dt = datetime.fromisoformat(result["datetime"])
    now = datetime.now(UTC)

    # Should be tomorrow
    assert parsed_dt.date() == (now + timedelta(days=1)).date()
    # Should be 3pm (15:00)
    assert parsed_dt.hour == 15


@pytest.mark.asyncio
async def test_parse_datetime_today(temporal_tool):
    """Test parsing 'today at 10:00'."""
    result = await temporal_tool.execute({
        "operation": "parse_datetime",
        "text": "today at 10:00",
    })

    parsed_dt = datetime.fromisoformat(result["datetime"])
    now = datetime.now(UTC)

    # Should be today
    assert parsed_dt.date() == now.date()
    # Should be 10:00
    assert parsed_dt.hour == 10


@pytest.mark.asyncio
async def test_parse_datetime_relative(temporal_tool):
    """Test parsing 'in 2 hours'."""
    result = await temporal_tool.execute({
        "operation": "parse_datetime",
        "text": "in 2 hours",
    })

    parsed_dt = datetime.fromisoformat(result["datetime"])
    now = datetime.now(UTC)

    # Should be approximately 2 hours from now
    time_diff = parsed_dt - now
    assert 1.9 < time_diff.total_seconds() / 3600 < 2.1  # Within 6 minutes


@pytest.mark.asyncio
async def test_parse_datetime_iso(temporal_tool):
    """Test parsing ISO format datetime."""
    iso_time = "2025-12-25T10:00:00+00:00"

    result = await temporal_tool.execute({
        "operation": "parse_datetime",
        "text": iso_time,
    })

    assert result["datetime"] == iso_time


@pytest.mark.asyncio
async def test_parse_date_today(temporal_tool):
    """Test parsing 'today' to date."""
    result = await temporal_tool.execute({
        "operation": "parse_date",
        "text": "today",
    })

    now = datetime.now(UTC)
    assert result["date"] == now.date().isoformat()


@pytest.mark.asyncio
async def test_parse_date_tomorrow(temporal_tool):
    """Test parsing 'tomorrow' to date."""
    result = await temporal_tool.execute({
        "operation": "parse_date",
        "text": "tomorrow",
    })

    tomorrow = (datetime.now(UTC) + timedelta(days=1)).date()
    assert result["date"] == tomorrow.isoformat()


@pytest.mark.asyncio
async def test_parse_date_yesterday(temporal_tool):
    """Test parsing 'yesterday' to date."""
    result = await temporal_tool.execute({
        "operation": "parse_date",
        "text": "yesterday",
    })

    yesterday = (datetime.now(UTC) - timedelta(days=1)).date()
    assert result["date"] == yesterday.isoformat()


@pytest.mark.asyncio
async def test_add_duration_hours(temporal_tool):
    """Test adding hours to a datetime."""
    base_dt = "2025-10-15T10:00:00+00:00"

    result = await temporal_tool.execute({
        "operation": "add_duration",
        "datetime": base_dt,
        "duration": "3 hours",
    })

    original = datetime.fromisoformat(base_dt)
    result_dt = datetime.fromisoformat(result["result"])

    assert result_dt == original + timedelta(hours=3)


@pytest.mark.asyncio
async def test_add_duration_days(temporal_tool):
    """Test adding days to a datetime."""
    base_dt = "2025-10-15T10:00:00+00:00"

    result = await temporal_tool.execute({
        "operation": "add_duration",
        "datetime": base_dt,
        "duration": "7 days",
    })

    original = datetime.fromisoformat(base_dt)
    result_dt = datetime.fromisoformat(result["result"])

    assert result_dt == original + timedelta(days=7)


@pytest.mark.asyncio
async def test_add_duration_minutes(temporal_tool):
    """Test adding minutes to a datetime."""
    base_dt = "2025-10-15T10:00:00+00:00"

    result = await temporal_tool.execute({
        "operation": "add_duration",
        "datetime": base_dt,
        "duration": "30 minutes",
    })

    original = datetime.fromisoformat(base_dt)
    result_dt = datetime.fromisoformat(result["result"])

    assert result_dt == original + timedelta(minutes=30)


@pytest.mark.asyncio
async def test_format_datetime(temporal_tool):
    """Test formatting a datetime."""
    dt = "2025-10-15T14:30:00+00:00"

    result = await temporal_tool.execute({
        "operation": "format_datetime",
        "datetime": dt,
        "format": "%B %d, %Y at %I:%M %p",
    })

    # Should format to "October 15, 2025 at 02:30 PM"
    assert "October" in result["formatted"]
    assert "15" in result["formatted"]
    assert "2025" in result["formatted"]


@pytest.mark.asyncio
async def test_format_datetime_default(temporal_tool):
    """Test formatting with default format."""
    dt = "2025-10-15T14:30:00+00:00"

    result = await temporal_tool.execute({
        "operation": "format_datetime",
        "datetime": dt,
    })

    # Should have formatted output
    assert "formatted" in result
    assert "2025" in result["formatted"]


@pytest.mark.asyncio
async def test_parse_time_am_pm(temporal_tool):
    """Test parsing AM/PM times."""
    # Test PM
    dt = datetime(2025, 10, 15, 0, 0, 0, tzinfo=UTC)
    result = temporal_tool._parse_time(dt, "3pm")
    assert result.hour == 15

    # Test AM
    result = temporal_tool._parse_time(dt, "10am")
    assert result.hour == 10

    # Test noon
    result = temporal_tool._parse_time(dt, "12pm")
    assert result.hour == 12

    # Test midnight
    result = temporal_tool._parse_time(dt, "12am")
    assert result.hour == 0


@pytest.mark.asyncio
async def test_parse_duration(temporal_tool):
    """Test parsing various duration strings."""
    # Hours
    delta = temporal_tool._parse_duration("2 hours")
    assert delta == timedelta(hours=2)

    # Days
    delta = temporal_tool._parse_duration("5 days")
    assert delta == timedelta(days=5)

    # Minutes
    delta = temporal_tool._parse_duration("30 minutes")
    assert delta == timedelta(minutes=30)

    # Weeks
    delta = temporal_tool._parse_duration("2 weeks")
    assert delta == timedelta(weeks=2)


@pytest.mark.asyncio
async def test_tool_metadata(temporal_tool):
    """Test TemporalTool metadata."""
    assert temporal_tool.name == "temporal_tool"
    assert "temporal" in temporal_tool.description.lower() or "date" in temporal_tool.description.lower()

    schema = temporal_tool.schema
    assert "operation" in schema["properties"]
    operations = schema["properties"]["operation"]["enum"]
    assert "parse_datetime" in operations
    assert "parse_date" in operations
    assert "add_duration" in operations
