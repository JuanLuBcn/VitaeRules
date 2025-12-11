"""Conversation state manager for enrichment sessions."""

import asyncio
from datetime import UTC, datetime

from .enrichment_types import EnrichmentContext


class ConversationStateManager:
    """Manages active enrichment conversations."""

    def __init__(self):
        """Initialize state manager."""
        self._active_contexts: dict[str, EnrichmentContext] = {}
        self._lock = asyncio.Lock()

    async def create_context(
        self, chat_id: str, agent_type: str, operation: str, data: dict
    ) -> EnrichmentContext:
        """
        Start new enrichment session.

        Args:
            chat_id: Chat/conversation identifier
            agent_type: Type of agent (list, task, note)
            operation: Operation to perform (add_item, create_task, etc.)
            data: Extracted data from user input

        Returns:
            New enrichment context
        """
        async with self._lock:
            context = EnrichmentContext(
                chat_id=chat_id,
                user_id=data.get("user_id", ""),
                agent_type=agent_type,
                operation=operation,
                original_data=data,
                missing_fields=[],
                asked_fields=[],
                gathered_data={},
                created_at=datetime.now(UTC).isoformat(),
            )
            self._active_contexts[chat_id] = context
            return context

    async def get_context(self, chat_id: str) -> EnrichmentContext | None:
        """
        Get active enrichment context for chat.

        Args:
            chat_id: Chat identifier

        Returns:
            Active context or None if no enrichment in progress
        """
        return self._active_contexts.get(chat_id)

    async def has_context(self, chat_id: str) -> bool:
        """Check if chat has active enrichment context."""
        return chat_id in self._active_contexts

    async def update_context(self, chat_id: str, context: EnrichmentContext):
        """
        Update existing context.

        Args:
            chat_id: Chat identifier
            context: Updated context
        """
        async with self._lock:
            context.last_updated = datetime.now(UTC).isoformat()
            self._active_contexts[chat_id] = context

    async def complete_context(self, chat_id: str) -> EnrichmentContext | None:
        """
        Mark enrichment as complete and remove from active.

        Args:
            chat_id: Chat identifier

        Returns:
            Completed context or None if not found
        """
        async with self._lock:
            return self._active_contexts.pop(chat_id, None)

    async def abandon_context(self, chat_id: str) -> None:
        """
        Abandon enrichment conversation (user wants to skip).

        Args:
            chat_id: Chat identifier
        """
        async with self._lock:
            self._active_contexts.pop(chat_id, None)

    async def get_all_contexts(self) -> dict[str, EnrichmentContext]:
        """Get all active contexts (for debugging/admin)."""
        return self._active_contexts.copy()

    async def cleanup_stale_contexts(self, max_age_minutes: int = 30) -> int:
        """
        Remove stale contexts that are too old.

        Args:
            max_age_minutes: Maximum age before considering stale

        Returns:
            Number of contexts cleaned up
        """
        from datetime import timedelta

        async with self._lock:
            now = datetime.now(UTC)
            stale_chats = []

            for chat_id, context in self._active_contexts.items():
                created = datetime.fromisoformat(context.created_at)
                age = now - created

                if age > timedelta(minutes=max_age_minutes):
                    stale_chats.append(chat_id)

            for chat_id in stale_chats:
                self._active_contexts.pop(chat_id)

            return len(stale_chats)
