"""Short-term memory (STM) implementation with SQLite."""

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ..config import get_settings
from ..tracing import get_tracer
from .schemas import ConversationMessage


class ShortTermMemory:
    """
    Short-term memory for conversation history.

    Stores recent messages per chat/session with windowing and TTL.
    Backed by SQLite for durability.
    """

    def __init__(self, db_path: Path | None = None, window_size: int = 50, ttl_hours: int = 24):
        """
        Initialize short-term memory.

        Args:
            db_path: Path to SQLite database (default: from settings)
            window_size: Maximum messages to keep per chat
            ttl_hours: Hours to keep messages before expiry
        """
        self.settings = get_settings()
        self.tracer = get_tracer()
        self.db_path = db_path or self.settings.sql_db_path
        self.window_size = window_size
        self.ttl_hours = ttl_hours

        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    chat_id TEXT NOT NULL,
                    user_id TEXT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    correlation_id TEXT,
                    metadata TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chat_timestamp ON conversations(chat_id, timestamp DESC)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_id ON conversations(chat_id)")
            conn.commit()

        self.tracer.debug(f"STM initialized at {self.db_path}")

    def add_message(self, message: ConversationMessage) -> None:
        """
        Add a message to conversation history.

        Args:
            message: Message to add
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO conversations (id, chat_id, user_id, role, content, timestamp, correlation_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    str(message.id),
                    message.chat_id,
                    message.user_id,
                    message.role,
                    message.content,
                    message.timestamp.isoformat(),
                    message.correlation_id,
                    str(message.metadata) if message.metadata else None,
                ),
            )
            conn.commit()

        self.tracer.debug(f"Added message to STM: chat={message.chat_id} role={message.role}")

        # Clean up old messages
        self._cleanup_chat(message.chat_id)

    def get_history(
        self, chat_id: str, limit: int | None = None, since: datetime | None = None
    ) -> list[ConversationMessage]:
        """
        Get conversation history for a chat.

        Args:
            chat_id: Chat identifier
            limit: Maximum messages to return (default: window_size)
            since: Only return messages after this timestamp

        Returns:
            List of messages, newest first
        """
        limit = limit or self.window_size

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT * FROM conversations WHERE chat_id = ?"
            params: list[Any] = [chat_id]

            if since:
                query += " AND timestamp > ?"
                params.append(since.isoformat())

            query += " ORDER BY timestamp DESC, ROWID DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()

        messages = []
        for row in rows:
            messages.append(
                ConversationMessage(
                    id=row["id"],
                    chat_id=row["chat_id"],
                    user_id=row["user_id"],
                    role=row["role"],
                    content=row["content"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    correlation_id=row["correlation_id"],
                    metadata=eval(row["metadata"]) if row["metadata"] else {},
                )
            )

        self.tracer.debug(f"Retrieved {len(messages)} messages from STM: chat={chat_id}")
        return messages

    def clear_chat(self, chat_id: str) -> int:
        """
        Clear all messages for a chat.

        Args:
            chat_id: Chat identifier

        Returns:
            Number of messages deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM conversations WHERE chat_id = ?", (chat_id,))
            deleted = cursor.rowcount
            conn.commit()

        self.tracer.debug(f"Cleared {deleted} messages from STM: chat={chat_id}")
        return deleted

    def _cleanup_chat(self, chat_id: str) -> None:
        """
        Clean up old messages for a chat based on window size and TTL.

        Args:
            chat_id: Chat identifier
        """
        cutoff_time = datetime.now(UTC) - timedelta(hours=self.ttl_hours)

        with sqlite3.connect(self.db_path) as conn:
            # Delete messages beyond TTL
            conn.execute(
                "DELETE FROM conversations WHERE chat_id = ? AND timestamp < ?",
                (chat_id, cutoff_time.isoformat()),
            )

            # Keep only window_size most recent messages
            conn.execute(
                """
                DELETE FROM conversations
                WHERE chat_id = ? AND id NOT IN (
                    SELECT id FROM conversations
                    WHERE chat_id = ?
                    ORDER BY timestamp DESC, ROWID DESC
                    LIMIT ?
                )
            """,
                (chat_id, chat_id, self.window_size),
            )
            conn.commit()

    def get_all_chats(self) -> list[str]:
        """
        Get list of all chat IDs with messages.

        Returns:
            List of chat IDs
        """
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT DISTINCT chat_id FROM conversations").fetchall()

        return [row[0] for row in rows]

    def get_message_count(self, chat_id: str) -> int:
        """
        Get total message count for a chat.

        Args:
            chat_id: Chat identifier

        Returns:
            Number of messages
        """
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM conversations WHERE chat_id = ?", (chat_id,)
            ).fetchone()

        return row[0] if row else 0
