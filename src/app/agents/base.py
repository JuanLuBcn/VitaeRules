"""Base agent interface for specialized agents."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class AgentResult:
    """Result from an agent execution."""
    
    success: bool
    message: str  # User-facing response
    data: dict[str, Any] | None = None  # Optional structured data
    needs_confirmation: bool = False  # Whether to ask user for confirmation
    preview: str | None = None  # Preview of what will be done
    error: str | None = None  # Error message if failed


class BaseAgent(ABC):
    """
    Base class for specialized agents.
    
    Each agent is responsible for:
    1. Understanding messages in its domain
    2. Extracting required information
    3. Asking for missing data if needed
    4. Executing actions via tools
    5. Providing user feedback
    """
    
    def __init__(self, llm_service, memory_service=None):
        """
        Initialize agent.
        
        Args:
            llm_service: LLM service for generating responses
            memory_service: Optional memory service for context
        """
        self.llm = llm_service
        self.memory = memory_service
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Agent name for logging and display."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """What this agent handles."""
        pass
    
    @abstractmethod
    async def can_handle(self, message: str) -> tuple[bool, float]:
        """
        Check if this agent can handle the message.
        
        Args:
            message: User message
            
        Returns:
            (can_handle, confidence) where confidence is 0.0-1.0
        """
        pass
    
    @abstractmethod
    async def handle(
        self, 
        message: str, 
        chat_id: str,
        user_id: str,
        context: dict[str, Any] | None = None
    ) -> AgentResult:
        """
        Handle a message in this agent's domain.
        
        Args:
            message: User message
            chat_id: Chat identifier
            user_id: User identifier
            context: Optional context (conversation history, etc.)
            
        Returns:
            AgentResult with success status and response
        """
        pass
    
    def _build_prompt(self, template: str, **kwargs) -> str:
        """
        Build a prompt from template and arguments.
        
        Args:
            template: Prompt template with {placeholders}
            **kwargs: Values to fill placeholders
            
        Returns:
            Formatted prompt
        """
        return template.format(**kwargs)
