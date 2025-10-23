"""Conversation session management for multi-turn interactions."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class ConversationState(str, Enum):
    """State of a conversational interaction."""
    
    INITIAL = "initial"                      # First message received
    GATHERING_DETAILS = "gathering_details"  # Asking follow-up questions
    CLARIFYING = "clarifying"               # Resolving ambiguity
    AWAITING_CONFIRMATION = "awaiting_confirmation"  # Waiting for yes/no
    EXECUTING = "executing"                  # Performing action
    COMPLETE = "complete"                    # Conversation finished


@dataclass
class ConversationSession:
    """
    Tracks state for multi-turn conversations.
    
    Manages enrichment flow: detection → follow-ups → confirmation → execution
    """
    
    # Identity
    user_id: str
    chat_id: str
    
    # State
    state: ConversationState = ConversationState.INITIAL
    started_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    # Intent & Action
    intent: str | None = None  # note_taking, task_create, question, etc.
    target_crew: str | None = None  # capture, retrieval
    
    # Data Collection
    original_message: str = ""
    collected_data: dict[str, Any] = field(default_factory=dict)
    follow_up_count: int = 0
    max_follow_ups: int = 3
    
    # Clarification (Phase 3)
    last_question: str = ""  # Last question asked (for corrections)
    clarification_options: list[dict[str, Any]] = field(default_factory=list)  # Options for ambiguous input
    
    # Pending Action
    pending_plan: dict[str, Any] | None = None  # Plan to execute after confirmation
    preview_message: str = ""  # Preview shown to user
    
    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()
    
    def is_expired(self, timeout_minutes: int = 5) -> bool:
        """Check if session has timed out."""
        return datetime.now() - self.last_activity > timedelta(minutes=timeout_minutes)
    
    def can_ask_more_questions(self) -> bool:
        """Check if we can ask more follow-up questions."""
        return self.follow_up_count < self.max_follow_ups
    
    def record_follow_up(self) -> None:
        """Increment follow-up counter."""
        self.follow_up_count += 1
        self.update_activity()
    
    def reset(self) -> None:
        """Reset session for new conversation."""
        self.state = ConversationState.INITIAL
        self.intent = None
        self.target_crew = None
        self.collected_data = {}
        self.follow_up_count = 0
        self.pending_plan = None
        self.preview_message = ""
        self.started_at = datetime.now()
        self.update_activity()


class SessionManager:
    """Manages conversation sessions for multiple users."""
    
    def __init__(self, timeout_minutes: int = 5):
        """
        Initialize session manager.
        
        Args:
            timeout_minutes: Minutes before session expires
        """
        self._sessions: dict[str, ConversationSession] = {}
        self.timeout_minutes = timeout_minutes
    
    def get_session(self, user_id: str, chat_id: str) -> ConversationSession:
        """
        Get or create session for user.
        
        Args:
            user_id: User identifier
            chat_id: Chat identifier
            
        Returns:
            Active or new conversation session
        """
        key = f"{user_id}:{chat_id}"
        
        # Check if session exists and is still valid
        if key in self._sessions:
            session = self._sessions[key]
            if not session.is_expired(self.timeout_minutes):
                session.update_activity()
                return session
            else:
                # Session expired - notify on next interaction
                del self._sessions[key]
        
        # Create new session
        session = ConversationSession(user_id=user_id, chat_id=chat_id)
        self._sessions[key] = session
        return session
    
    def clear_session(self, user_id: str, chat_id: str) -> None:
        """
        Clear session for user.
        
        Args:
            user_id: User identifier
            chat_id: Chat identifier
        """
        key = f"{user_id}:{chat_id}"
        if key in self._sessions:
            del self._sessions[key]
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        expired_keys = [
            key for key, session in self._sessions.items()
            if session.is_expired(self.timeout_minutes)
        ]
        
        for key in expired_keys:
            del self._sessions[key]
        
        return len(expired_keys)
    
    def get_active_count(self) -> int:
        """Get count of active sessions."""
        return len(self._sessions)
