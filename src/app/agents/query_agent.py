"""Query and retrieval agent."""

from typing import Any

from app.crews.retrieval import RetrievalCrew
from app.llm import LLMService
from app.tracing import get_tracer

from .base import AgentResult, BaseAgent

logger = get_tracer()


class QueryAgent(BaseAgent):
    """
    Handles questions and information retrieval.
    
    Understands:
    - "What did I do yesterday?"
    - "Tell me about John"
    - "When is the project deadline?"
    - "What are my notes about coffee?"
    """
    
    def __init__(self, memory_service, retrieval_crew: RetrievalCrew):
        """Initialize query agent."""
        self.memory = memory_service
        self.retrieval_crew = retrieval_crew
    
    @property
    def name(self) -> str:
        """Agent name."""
        return "QueryAgent"
    
    @property
    def description(self) -> str:
        """Agent description."""
        return "Answers questions by searching memories and notes"
    
    async def can_handle(self, message: str) -> tuple[bool, float]:
        """Check if message is a question."""
        message_lower = message.lower()
        
        # Question words
        question_words = [
            "what", "qué", "cuando", "when", "where", "dónde",
            "who", "quién", "how", "cómo", "why", "por qué",
            "cuándo", "cuál", "cuáles", "tell me", "dime"
        ]
        
        if any(word in message_lower for word in question_words):
            return True, 0.85
        
        # Question marks
        if "?" in message:
            return True, 0.9
        
        return False, 0.0
    
    async def handle(
        self,
        message: str,
        chat_id: str,
        user_id: str,
        context: dict[str, Any] | None = None
    ) -> AgentResult:
        """Handle query by retrieving relevant information."""
        logger.info(f"QueryAgent handling: {message[:100]}")
        
        try:
            # Use retrieval crew to find relevant memories and compose answer
            from app.crews.retrieval import RetrievalContext
            
            retrieval_context = RetrievalContext(
                chat_id=chat_id,
                user_id=user_id,
                memory_service=self.memory,
            )
            
            result = self.retrieval_crew.retrieve(
                user_question=message,
                context=retrieval_context,
            )
            
            answer = result.answer.answer if result.answer else "No tengo información sobre eso."
            sources = result.memories if result.memories else []
            
            # Format response with sources
            response = answer
            
            if sources:
                response += "\n\n📚 **Fuentes:**"
                for i, source in enumerate(sources[:3], 1):  # Show max 3 sources
                    snippet = source.content[:100] if hasattr(source, 'content') else str(source)[:100]
                    response += f"\n{i}. {snippet}..."
            
            return AgentResult(
                success=True,
                message=response,
                data={
                    "answer": answer,
                    "sources": sources,
                    "query": message,
                }
            )
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return AgentResult(
                success=False,
                message="Lo siento, no pude encontrar una respuesta a tu pregunta.",
                error=str(e)
            )
