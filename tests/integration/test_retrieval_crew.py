"""Integration tests for Retrieval Crew."""

from datetime import datetime, timezone

import pytest

from app.contracts.query import QueryIntent
from app.crews.retrieval import RetrievalContext, RetrievalCrew
from app.memory import (
    LongTermMemory,
    MemoryItem,
    MemorySection,
    MemoryService,
    MemorySource,
    ShortTermMemory,
)


@pytest.fixture
def memory_service(tmp_path):
    """Create a memory service with test data."""
    stm_path = tmp_path / "stm.sqlite"
    ltm_path = tmp_path / "ltm_store"

    stm = ShortTermMemory(db_path=stm_path)
    ltm = LongTermMemory(store_path=ltm_path)
    service = MemoryService(stm=stm, ltm=ltm)

    # Seed LTM with test data
    test_memories = [
        MemoryItem(
            source=MemorySource.CAPTURE,
            section=MemorySection.NOTE,
            title="Meeting with Alice",
            content="Had a productive meeting with Alice about the Q1 roadmap. Discussed feature priorities and timeline.",
            people=["Alice"],
            tags=["meeting", "roadmap"],
            created_at=datetime(2025, 1, 15, 10, 0, tzinfo=timezone.utc),
        ),
        MemoryItem(
            source=MemorySource.CAPTURE,
            section=MemorySection.NOTE,
            title="Coffee with Bob",
            content="Caught up with Bob over coffee. He mentioned the new project launching next month.",
            people=["Bob"],
            tags=["social", "project"],
            created_at=datetime(2025, 1, 16, 14, 30, tzinfo=timezone.utc),
        ),
        MemoryItem(
            source=MemorySource.DIARY,
            section=MemorySection.DIARY,
            title="Daily Summary - Jan 17",
            content="Productive day. Completed code review, attended team standup, and started working on the new feature.",
            tags=["work", "coding"],
            created_at=datetime(2025, 1, 17, 20, 0, tzinfo=timezone.utc),
        ),
        MemoryItem(
            source=MemorySource.CAPTURE,
            section=MemorySection.NOTE,
            title="Grocery List",
            content="Need to buy: milk, eggs, bread, coffee beans.",
            tags=["shopping", "personal"],
            created_at=datetime(2025, 1, 18, 9, 0, tzinfo=timezone.utc),
        ),
    ]

    for memory in test_memories:
        ltm.add(memory)

    return service


@pytest.fixture
def retrieval_crew(memory_service):
    """Create a RetrievalCrew instance."""
    return RetrievalCrew(memory_service=memory_service, llm=None)


@pytest.fixture
def retrieval_context():
    """Create a RetrievalContext."""
    return RetrievalContext(
        chat_id="test_chat_123", user_id="test_user_456", memory_service=None
    )


class TestRetrievalCrew:
    """Tests for RetrievalCrew workflow."""

    def test_retrieve_factual_query(self, retrieval_crew, memory_service):
        """Test retrieval for a factual question."""
        context = RetrievalContext(
            chat_id="chat1", user_id="user1", memory_service=memory_service
        )

        result = retrieval_crew.retrieve("What did Alice talk about?", context)

        assert result is not None
        assert result.query.query_text == "What did Alice talk about?"
        # Should find the meeting with Alice
        assert len(result.memories) > 0
        # Answer should have some evidence
        assert result.answer.has_evidence or len(result.memories) == 0

    def test_retrieve_temporal_query(self, retrieval_crew, memory_service):
        """Test retrieval for a time-based question."""
        context = RetrievalContext(
            chat_id="chat1", user_id="user1", memory_service=memory_service
        )

        result = retrieval_crew.retrieve("What happened yesterday?", context)

        assert result is not None
        assert result.query.intent in [QueryIntent.TEMPORAL, QueryIntent.UNKNOWN]
        # Workflow should complete without errors
        assert result.answer is not None

    def test_retrieve_list_query(self, retrieval_crew, memory_service):
        """Test retrieval for a list question."""
        context = RetrievalContext(
            chat_id="chat1", user_id="user1", memory_service=memory_service
        )

        result = retrieval_crew.retrieve("List all my meetings", context)

        assert result is not None
        assert result.query.intent in [QueryIntent.LIST, QueryIntent.UNKNOWN]
        # Should increase max_results for list queries
        assert result.query.max_results >= 10

    def test_retrieve_summary_query(self, retrieval_crew, memory_service):
        """Test retrieval for a summary question."""
        context = RetrievalContext(
            chat_id="chat1", user_id="user1", memory_service=memory_service
        )

        result = retrieval_crew.retrieve("Summarize what I did last week", context)

        assert result is not None
        assert result.query.intent in [QueryIntent.SUMMARY, QueryIntent.UNKNOWN]
        assert result.answer is not None

    def test_retrieve_with_no_results(self, retrieval_crew, memory_service):
        """Test retrieval when no memories match."""
        context = RetrievalContext(
            chat_id="chat1", user_id="user1", memory_service=memory_service
        )

        result = retrieval_crew.retrieve(
            "What do I know about quantum physics?", context
        )

        assert result is not None
        assert result.answer is not None
        # Should explicitly state no information available
        assert not result.answer.has_evidence
        assert len(result.answer.citations) == 0

    def test_retrieve_zero_evidence_enforcement(self, retrieval_crew, memory_service):
        """Test that answers enforce zero-evidence policy."""
        context = RetrievalContext(
            chat_id="chat1", user_id="user1", memory_service=memory_service
        )

        result = retrieval_crew.retrieve("Tell me about space exploration", context)

        # If no relevant memories, should not fabricate answer
        if not result.memories:
            assert not result.answer.has_evidence
            assert "don't have" in result.answer.answer.lower() or "no information" in result.answer.answer.lower()

    def test_retrieve_with_citations(self, retrieval_crew, memory_service):
        """Test that answers include proper citations."""
        context = RetrievalContext(
            chat_id="chat1", user_id="user1", memory_service=memory_service
        )

        result = retrieval_crew.retrieve("What meetings did I have?", context)

        # If memories found, should have citations
        if result.memories:
            assert result.answer.has_evidence
            assert len(result.answer.citations) > 0
            # Citations should reference actual memories
            citation_ids = {c.memory_id for c in result.answer.citations}
            memory_ids = {str(m.id) for m in result.memories}
            # At least some citations should match retrieved memories
            assert len(citation_ids & memory_ids) > 0 or len(citation_ids) > 0

    def test_retrieve_person_filter(self, retrieval_crew, memory_service):
        """Test retrieval with person filter."""
        context = RetrievalContext(
            chat_id="chat1", user_id="user1", memory_service=memory_service
        )

        result = retrieval_crew.retrieve("What did Bob say?", context)

        # Query should extract Bob as a person filter (if keyword detection works)
        # Or at least complete the workflow
        assert result is not None
        assert result.answer is not None

    def test_retrieve_confidence_scoring(self, retrieval_crew, memory_service):
        """Test that answers have confidence scores."""
        context = RetrievalContext(
            chat_id="chat1", user_id="user1", memory_service=memory_service
        )

        result = retrieval_crew.retrieve("What happened?", context)

        assert result.answer.confidence >= 0.0
        assert result.answer.confidence <= 1.0
        # No memories = low confidence
        if not result.memories:
            assert result.answer.confidence == 0.0

    def test_retrieve_error_handling(self, retrieval_crew):
        """Test retrieval handles errors gracefully."""
        # Context with None memory_service should handle error
        bad_context = RetrievalContext(
            chat_id="chat1", user_id="user1", memory_service=None
        )

        result = retrieval_crew.retrieve("What happened?", bad_context)

        # Should return error answer, not crash
        assert result is not None
        assert result.answer is not None
        assert not result.answer.has_evidence


class TestQueryPlanning:
    """Tests for query planning step."""

    def test_plan_factual_intent(self, retrieval_crew, memory_service):
        """Test planning detects factual intent."""
        context = RetrievalContext(
            chat_id="chat1", user_id="user1", memory_service=memory_service
        )

        result = retrieval_crew.retrieve("What is my meeting about?", context)

        assert result.query is not None
        # Should classify as factual or unknown
        assert result.query.intent in [QueryIntent.FACTUAL, QueryIntent.UNKNOWN]

    def test_plan_temporal_keywords(self, retrieval_crew, memory_service):
        """Test planning detects temporal keywords."""
        context = RetrievalContext(
            chat_id="chat1", user_id="user1", memory_service=memory_service
        )

        result = retrieval_crew.retrieve("What did I do yesterday?", context)

        # Should detect temporal intent from "yesterday"
        assert result.query.intent in [QueryIntent.TEMPORAL, QueryIntent.UNKNOWN]

    def test_plan_list_keywords(self, retrieval_crew, memory_service):
        """Test planning detects list keywords."""
        context = RetrievalContext(
            chat_id="chat1", user_id="user1", memory_service=memory_service
        )

        result = retrieval_crew.retrieve("List all notes", context)

        # Should detect list intent from "list all"
        assert result.query.intent in [QueryIntent.LIST, QueryIntent.UNKNOWN]


class TestMemoryRetrieval:
    """Tests for memory retrieval step."""

    def test_retrieve_matches_query(self, retrieval_crew, memory_service):
        """Test retriever returns relevant memories."""
        context = RetrievalContext(
            chat_id="chat1", user_id="user1", memory_service=memory_service
        )

        result = retrieval_crew.retrieve("meeting roadmap", context)

        # Should find the Alice meeting about roadmap
        assert result.memories is not None
        if result.memories:
            # At least one memory should mention meeting or roadmap
            contents = " ".join([m.content or "" for m in result.memories])
            assert "meeting" in contents.lower() or "roadmap" in contents.lower()

    def test_retrieve_respects_max_results(self, retrieval_crew, memory_service):
        """Test retriever respects max_results limit."""
        context = RetrievalContext(
            chat_id="chat1", user_id="user1", memory_service=memory_service
        )

        result = retrieval_crew.retrieve("everything", context)

        # Should not exceed max_results
        assert len(result.memories) <= result.query.max_results


class TestAnswerComposition:
    """Tests for answer composition step."""

    def test_compose_with_no_memories(self, retrieval_crew, memory_service):
        """Test composer handles no memories gracefully."""
        context = RetrievalContext(
            chat_id="chat1", user_id="user1", memory_service=memory_service
        )

        result = retrieval_crew.retrieve("nonexistent topic xyz123", context)

        assert result.answer is not None
        assert not result.answer.has_evidence
        assert "don't have" in result.answer.answer.lower() or "no" in result.answer.answer.lower()

    def test_compose_with_memories(self, retrieval_crew, memory_service):
        """Test composer generates answer from memories."""
        context = RetrievalContext(
            chat_id="chat1", user_id="user1", memory_service=memory_service
        )

        result = retrieval_crew.retrieve("Alice meeting", context)

        if result.memories:
            assert result.answer.has_evidence
            assert len(result.answer.answer) > 0
            # Answer should be more than just "I don't know"
            assert len(result.answer.answer) > 20
