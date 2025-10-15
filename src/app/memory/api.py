"""Unified memory API combining STM and LTM."""

from datetime import datetime
from uuid import UUID

from ..config import get_settings
from ..tracing import TraceEvent, get_tracer
from .long_term import LongTermMemory
from .schemas import (
    ConversationMessage,
    MemoryItem,
    MemoryQuery,
    MemorySearchResult,
    MemorySection,
)
from .short_term import ShortTermMemory


class MemoryService:
    """
    Unified memory service combining short-term and long-term memory.

    Provides a single interface for agents to access conversation history
    and semantic search over long-term memories.
    """

    def __init__(
        self,
        stm: ShortTermMemory | None = None,
        ltm: LongTermMemory | None = None,
    ):
        """
        Initialize memory service.

        Args:
            stm: Short-term memory instance (created if None)
            ltm: Long-term memory instance (created if None)
        """
        self.settings = get_settings()
        self.tracer = get_tracer()

        # Initialize STM and LTM
        self.stm = stm or ShortTermMemory()
        self.ltm = ltm or LongTermMemory()

        self.tracer.info("Memory service initialized")

    # ========== Short-term Memory (STM) Methods ==========

    def add_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        user_id: str | None = None,
        correlation_id: str | None = None,
    ) -> ConversationMessage:
        """
        Add a message to conversation history.

        Args:
            chat_id: Chat identifier
            role: Message role (user, assistant, system)
            content: Message content
            user_id: Optional user identifier
            correlation_id: Optional correlation ID for tracing

        Returns:
            Created message
        """
        message = ConversationMessage(
            chat_id=chat_id,
            user_id=user_id,
            role=role,
            content=content,
            correlation_id=correlation_id,
        )

        self.stm.add_message(message)

        self.tracer.trace(
            TraceEvent.MEMORY_READ,
            chat_id=chat_id,
            correlation_id=correlation_id,
            preview=f"Added {role} message",
        )

        return message

    def get_conversation_history(
        self,
        chat_id: str,
        limit: int | None = None,
        since: datetime | None = None,
    ) -> list[ConversationMessage]:
        """
        Get conversation history for a chat.

        Args:
            chat_id: Chat identifier
            limit: Maximum messages to return
            since: Only return messages after this timestamp

        Returns:
            List of messages, newest first
        """
        messages = self.stm.get_history(chat_id, limit=limit, since=since)

        self.tracer.trace(
            TraceEvent.MEMORY_READ,
            chat_id=chat_id,
            preview=f"Retrieved {len(messages)} messages",
        )

        return messages

    def clear_conversation(self, chat_id: str) -> int:
        """
        Clear conversation history for a chat.

        Args:
            chat_id: Chat identifier

        Returns:
            Number of messages deleted
        """
        deleted = self.stm.clear_chat(chat_id)

        self.tracer.trace(
            TraceEvent.MEMORY_WRITE,
            chat_id=chat_id,
            preview=f"Cleared {deleted} messages",
        )

        return deleted

    # ========== Long-term Memory (LTM) Methods ==========

    def save_memory(self, item: MemoryItem) -> MemoryItem:
        """
        Save a memory item to long-term memory.

        Args:
            item: Memory item to save

        Returns:
            Saved memory item
        """
        self.ltm.add(item)

        self.tracer.trace(
            TraceEvent.MEMORY_WRITE,
            chat_id=item.chat_id,
            user_id=item.user_id,
            preview=f"Saved: {item.title}",
            section=item.section if isinstance(item.section, str) else item.section.value,
        )

        return item

    def get_memory(self, item_id: UUID | str) -> MemoryItem | None:
        """
        Get a memory item by ID.

        Args:
            item_id: Item identifier

        Returns:
            Memory item or None if not found
        """
        item = self.ltm.get(item_id)

        if item:
            self.tracer.trace(
                TraceEvent.MEMORY_READ,
                preview=f"Retrieved: {item.title}",
            )

        return item

    def search_memories(self, query: MemoryQuery) -> list[MemorySearchResult]:
        """
        Search for relevant memories using semantic search.

        Args:
            query: Search query with filters

        Returns:
            List of search results with relevance scores
        """
        results = self.ltm.search(query)

        self.tracer.trace(
            TraceEvent.RETRIEVAL_RESULTS,
            preview=f"Search: '{query.query}' -> {len(results)} results",
            top_k=query.top_k,
        )

        return results

    def update_memory(self, item: MemoryItem) -> MemoryItem:
        """
        Update an existing memory item.

        Args:
            item: Updated memory item

        Returns:
            Updated memory item
        """
        self.ltm.update(item)

        self.tracer.trace(
            TraceEvent.MEMORY_WRITE,
            preview=f"Updated: {item.title}",
        )

        return item

    def delete_memory(self, item_id: UUID | str) -> None:
        """
        Delete a memory item.

        Args:
            item_id: Item identifier
        """
        self.ltm.delete(item_id)

        self.tracer.trace(
            TraceEvent.MEMORY_WRITE,
            preview=f"Deleted: {item_id}",
        )

    def count_memories(self, section: MemorySection | None = None) -> int:
        """
        Count memory items.

        Args:
            section: Optional section filter

        Returns:
            Number of items
        """
        return self.ltm.count(section)

    # ========== Convenience Methods ==========

    def get_recent_context(
        self,
        chat_id: str,
        message_limit: int = 10,
    ) -> str:
        """
        Get recent conversation context as formatted text.

        Args:
            chat_id: Chat identifier
            message_limit: Number of recent messages

        Returns:
            Formatted conversation context
        """
        messages = self.get_conversation_history(chat_id, limit=message_limit)

        # Format messages (reverse to chronological order)
        lines = []
        for msg in reversed(messages):
            lines.append(f"{msg.role}: {msg.content}")

        return "\n".join(lines)

    def create_note(
        self,
        title: str,
        content: str,
        chat_id: str | None = None,
        user_id: str | None = None,
        **kwargs,
    ) -> MemoryItem:
        """
        Create a note memory item.

        Args:
            title: Note title
            content: Note content
            chat_id: Optional chat ID
            user_id: Optional user ID
            **kwargs: Additional MemoryItem fields

        Returns:
            Created memory item
        """
        from .schemas import MemorySource

        item = MemoryItem(
            source=MemorySource.CAPTURE,
            section=MemorySection.NOTE,
            title=title,
            content=content,
            chat_id=chat_id,
            user_id=user_id,
            **kwargs,
        )

        return self.save_memory(item)


# Global memory service instance
_memory_service: MemoryService | None = None


def get_memory_service() -> MemoryService:
    """Get or create the global memory service instance."""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service


def reload_memory_service() -> MemoryService:
    """Reload memory service (useful for testing)."""
    global _memory_service
    _memory_service = MemoryService()
    return _memory_service
