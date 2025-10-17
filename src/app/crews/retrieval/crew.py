"""
RetrievalCrew orchestrator.

Coordinates QueryPlanner → Retriever → Composer workflow for question answering.
"""

from dataclasses import dataclass

from app.contracts.query import GroundedAnswer, Query
from app.memory import MemoryItem, MemoryService
from app.tracing import get_tracer

from .composer import compose_answer
from .query_planner import plan_query_from_question
from .retriever import retrieve_memories

logger = get_tracer()


@dataclass
class RetrievalContext:
    """Context for retrieval operations."""

    chat_id: str
    user_id: str
    memory_service: MemoryService


@dataclass
class RetrievalResult:
    """Result of retrieval workflow."""

    query: Query
    memories: list[MemoryItem]
    answer: GroundedAnswer


class RetrievalCrew:
    """
    Orchestrates the Retrieval Crew workflow.

    QueryPlanner: Analyzes question → structured Query
    Retriever: Searches LTM → relevant MemoryItems
    Composer: Generates grounded answer with citations
    """

    def __init__(self, memory_service: MemoryService, llm=None):
        """
        Initialize RetrievalCrew.

        Args:
            memory_service: Memory service for LTM access
            llm: Language model for agents (optional, defaults to config)
        """
        self.memory_service = memory_service
        self.llm = llm
        self.tracer = get_tracer()

    def retrieve(self, user_question: str, context: RetrievalContext) -> RetrievalResult:
        """
        Execute retrieval workflow to answer a question.

        Workflow:
        1. QueryPlanner: Parse question → Query
        2. Retriever: Search LTM → MemoryItems
        3. Composer: Generate GroundedAnswer with citations

        Args:
            user_question: The user's natural language question
            context: Retrieval context with chat/user IDs and memory service

        Returns:
            RetrievalResult with query, memories, and grounded answer
        """
        self.tracer.info(f"Starting retrieval for question: {user_question}")

        try:
            # Step 1: Plan the query
            query = plan_query_from_question(
                user_question, context.chat_id, context.user_id, self.llm
            )
            self.tracer.info(
                f"Query planned: intent={query.intent.value}, filters={query.filters.model_dump()}"
            )

            # Step 2: Retrieve memories
            memories = retrieve_memories(
                query, context.chat_id, context.user_id, context.memory_service, self.llm
            )
            self.tracer.info(f"Retrieved {len(memories)} memories")

            # Step 3: Compose answer
            answer = compose_answer(
                query, memories, context.chat_id, context.user_id, self.llm
            )
            self.tracer.info(
                f"Answer composed: has_evidence={answer.has_evidence}, confidence={answer.confidence}"
            )

            return RetrievalResult(query=query, memories=memories, answer=answer)

        except Exception as e:
            self.tracer.error(f"Retrieval workflow failed: {e}")

            # Return error response
            return RetrievalResult(
                query=Query(query_text=user_question),
                memories=[],
                answer=GroundedAnswer(
                    query=user_question,
                    answer=f"I encountered an error: {str(e)}",
                    citations=[],
                    confidence=0.0,
                    has_evidence=False,
                    reasoning=f"Error: {str(e)}",
                ),
            )
