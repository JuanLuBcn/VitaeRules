"""TemporalTool for date/time parsing and normalization."""

from datetime import UTC, datetime, timedelta
from typing import Any

from ..contracts import BaseTool
from ..tracing import get_tracer


class TemporalTool(BaseTool):
    """
    Tool for parsing and normalizing temporal expressions.

    Operations:
    - parse_datetime: Parse natural language date/time to ISO format
    - parse_date: Parse natural language date to ISO date
    - add_duration: Add duration to a datetime
    - format_datetime: Format datetime for display
    """

    def __init__(self):
        """Initialize TemporalTool."""
        self.tracer = get_tracer()
        self.tracer.debug("TemporalTool initialized")

    @property
    def name(self) -> str:
        """Tool name."""
        return "temporal_tool"

    @property
    def description(self) -> str:
        """Tool description."""
        return (
            "Parse and normalize dates, times, and temporal expressions. "
            "Operations: parse_datetime, parse_date, add_duration, format_datetime"
        )

    @property
    def schema(self) -> dict[str, Any]:
        """JSON Schema for tool arguments."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "parse_datetime",
                        "parse_date",
                        "add_duration",
                        "format_datetime",
                    ],
                    "description": "Operation to perform",
                },
                "text": {
                    "type": "string",
                    "description": "Natural language temporal expression (for parse operations)",
                },
                "datetime": {
                    "type": "string",
                    "description": "ISO datetime string (for add_duration, format_datetime)",
                },
                "duration": {
                    "type": "string",
                    "description": "Duration string like '2 hours', '3 days' (for add_duration)",
                },
                "format": {
                    "type": "string",
                    "description": "Output format (for format_datetime)",
                },
                "timezone": {
                    "type": "string",
                    "description": "Timezone for parsing/formatting",
                },
            },
            "required": ["operation"],
        }

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute the temporal operation."""
        operation = arguments["operation"]

        if operation == "parse_datetime":
            return await self._parse_datetime(arguments)
        elif operation == "parse_date":
            return await self._parse_date(arguments)
        elif operation == "add_duration":
            return await self._add_duration(arguments)
        elif operation == "format_datetime":
            return await self._format_datetime(arguments)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    async def _parse_datetime(self, args: dict[str, Any]) -> dict[str, Any]:
        """
        Parse natural language datetime to ISO format.

        Supports common patterns like:
        - "tomorrow at 3pm"
        - "next monday 10:00"
        - "in 2 hours"
        """
        text = args.get("text", "").lower().strip()
        if not text:
            raise ValueError("text is required for parse_datetime")

        now = datetime.now(UTC)

        # Simple pattern matching
        if "tomorrow" in text:
            dt = now + timedelta(days=1)
            # Try to extract time
            if "at" in text:
                time_part = text.split("at")[1].strip()
                dt = self._parse_time(dt, time_part)
        elif "today" in text:
            dt = now
            if "at" in text:
                time_part = text.split("at")[1].strip()
                dt = self._parse_time(dt, time_part)
        elif "in" in text:
            # "in 2 hours", "in 30 minutes"
            dt = self._parse_relative_time(now, text)
        else:
            # Try ISO format
            try:
                dt = datetime.fromisoformat(text)
            except ValueError:
                raise ValueError(f"Unable to parse datetime: {text}")

        return {
            "datetime": dt.isoformat(),
            "timestamp": dt.timestamp(),
            "parsed_text": text,
        }

    async def _parse_date(self, args: dict[str, Any]) -> dict[str, Any]:
        """Parse natural language date to ISO date format."""
        text = args.get("text", "").lower().strip()
        if not text:
            raise ValueError("text is required for parse_date")

        now = datetime.now(UTC)

        if text in ["today", "now"]:
            dt = now
        elif text == "tomorrow":
            dt = now + timedelta(days=1)
        elif text == "yesterday":
            dt = now - timedelta(days=1)
        else:
            # Try ISO format
            try:
                dt = datetime.fromisoformat(text)
            except ValueError:
                raise ValueError(f"Unable to parse date: {text}")

        return {
            "date": dt.date().isoformat(),
            "datetime": dt.isoformat(),
            "parsed_text": text,
        }

    async def _add_duration(self, args: dict[str, Any]) -> dict[str, Any]:
        """Add duration to a datetime."""
        datetime_str = args.get("datetime")
        if not datetime_str:
            raise ValueError("datetime is required for add_duration")

        duration_str = args.get("duration", "").lower().strip()
        if not duration_str:
            raise ValueError("duration is required for add_duration")

        dt = datetime.fromisoformat(datetime_str)

        # Parse duration
        delta = self._parse_duration(duration_str)
        new_dt = dt + delta

        return {
            "original": dt.isoformat(),
            "duration": duration_str,
            "result": new_dt.isoformat(),
        }

    async def _format_datetime(self, args: dict[str, Any]) -> dict[str, Any]:
        """Format datetime for display."""
        datetime_str = args.get("datetime")
        if not datetime_str:
            raise ValueError("datetime is required for format_datetime")

        dt = datetime.fromisoformat(datetime_str)
        format_str = args.get("format", "%Y-%m-%d %H:%M:%S")

        return {
            "datetime": dt.isoformat(),
            "formatted": dt.strftime(format_str),
            "format": format_str,
        }

    def _parse_time(self, dt: datetime, time_str: str) -> datetime:
        """Parse time string and apply to datetime."""
        time_str = time_str.strip().lower()

        # Handle AM/PM
        hour = 0
        minute = 0

        if "pm" in time_str or "am" in time_str:
            is_pm = "pm" in time_str
            time_str = time_str.replace("pm", "").replace("am", "").strip()

            if ":" in time_str:
                parts = time_str.split(":")
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
            else:
                hour = int(time_str)

            if is_pm and hour != 12:
                hour += 12
            elif not is_pm and hour == 12:
                hour = 0
        else:
            # 24-hour format
            if ":" in time_str:
                parts = time_str.split(":")
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
            else:
                hour = int(time_str)

        return dt.replace(hour=hour, minute=minute, second=0, microsecond=0)

    def _parse_relative_time(self, now: datetime, text: str) -> datetime:
        """Parse relative time like 'in 2 hours'."""
        text = text.strip().lower()

        # Extract number and unit
        words = text.split()
        if "in" in words:
            idx = words.index("in")
            if len(words) > idx + 2:
                num = int(words[idx + 1])
                unit = words[idx + 2]

                delta = self._duration_to_timedelta(num, unit)
                return now + delta

        raise ValueError(f"Unable to parse relative time: {text}")

    def _parse_duration(self, duration_str: str) -> timedelta:
        """Parse duration string to timedelta."""
        words = duration_str.split()
        if len(words) >= 2:
            num = int(words[0])
            unit = words[1]
            return self._duration_to_timedelta(num, unit)

        raise ValueError(f"Unable to parse duration: {duration_str}")

    def _duration_to_timedelta(self, num: int, unit: str) -> timedelta:
        """Convert number and unit to timedelta."""
        unit = unit.lower().rstrip("s")  # Remove plural 's'

        if unit in ["second", "sec"]:
            return timedelta(seconds=num)
        elif unit in ["minute", "min"]:
            return timedelta(minutes=num)
        elif unit in ["hour", "hr", "h"]:
            return timedelta(hours=num)
        elif unit in ["day", "d"]:
            return timedelta(days=num)
        elif unit in ["week", "wk", "w"]:
            return timedelta(weeks=num)
        else:
            raise ValueError(f"Unknown time unit: {unit}")
