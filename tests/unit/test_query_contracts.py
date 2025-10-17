"""Unit tests for Query contracts."""

from datetime import datetime, timezone

import pytest

from app.contracts.query import (
    Citation,
    DateRange,
    GroundedAnswer,
    Query,
    QueryFilters,
    QueryIntent,
)


class TestQueryIntent:
    """Tests for QueryIntent enum."""

    def test_intent_values(self):
        """Test all intent enum values exist."""
        assert QueryIntent.FACTUAL == "factual"
        assert QueryIntent.TEMPORAL == "temporal"
        assert QueryIntent.LIST == "list"
        assert QueryIntent.SUMMARY == "summary"
        assert QueryIntent.UNKNOWN == "unknown"

    def test_intent_membership(self):
        """Test intent values are valid."""
        assert "factual" in [intent.value for intent in QueryIntent]
        assert "temporal" in [intent.value for intent in QueryIntent]


class TestDateRange:
    """Tests for DateRange model."""

    def test_date_range_empty(self):
        """Test DateRange with no dates."""
        dr = DateRange()
        assert dr.start is None
        assert dr.end is None

    def test_date_range_with_dates(self):
        """Test DateRange with start and end."""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 12, 31, tzinfo=timezone.utc)
        dr = DateRange(start=start, end=end)
        assert dr.start == start
        assert dr.end == end

    def test_date_range_partial(self):
        """Test DateRange with only start or end."""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        dr = DateRange(start=start)
        assert dr.start == start
        assert dr.end is None


class TestQueryFilters:
    """Tests for QueryFilters model."""

    def test_filters_empty(self):
        """Test QueryFilters with no filters."""
        filters = QueryFilters()
        assert filters.people == []
        assert filters.places == []
        assert filters.tags == []
        assert filters.date_range is None
        assert filters.sections == []

    def test_filters_with_data(self):
        """Test QueryFilters with all fields."""
        dr = DateRange(start=datetime(2025, 1, 1, tzinfo=timezone.utc))
        filters = QueryFilters(
            people=["Alice", "Bob"],
            places=["Home", "Office"],
            tags=["work", "personal"],
            date_range=dr,
            sections=["diary", "task"],
        )
        assert filters.people == ["Alice", "Bob"]
        assert filters.places == ["Home", "Office"]
        assert filters.tags == ["work", "personal"]
        assert filters.date_range == dr
        assert filters.sections == ["diary", "task"]


class TestQuery:
    """Tests for Query model."""

    def test_query_minimal(self):
        """Test Query with only query_text."""
        query = Query(query_text="What did I do yesterday?")
        assert query.query_text == "What did I do yesterday?"
        assert query.intent == QueryIntent.UNKNOWN
        assert isinstance(query.filters, QueryFilters)
        assert query.max_results == 10
        assert query.reasoning is None

    def test_query_complete(self):
        """Test Query with all fields."""
        filters = QueryFilters(people=["Alice"], tags=["meeting"])
        query = Query(
            query_text="What meetings did I have with Alice?",
            intent=QueryIntent.LIST,
            filters=filters,
            max_results=20,
            reasoning="Detected list intent with person filter",
        )
        assert query.query_text == "What meetings did I have with Alice?"
        assert query.intent == QueryIntent.LIST
        assert query.filters.people == ["Alice"]
        assert query.max_results == 20
        assert "list intent" in query.reasoning

    def test_query_max_results_validation(self):
        """Test Query max_results bounds."""
        # Valid range
        query = Query(query_text="test", max_results=50)
        assert query.max_results == 50

        # Test boundaries
        query = Query(query_text="test", max_results=1)
        assert query.max_results == 1

        query = Query(query_text="test", max_results=100)
        assert query.max_results == 100

        # Invalid values should raise validation error
        with pytest.raises(Exception):  # Pydantic ValidationError
            Query(query_text="test", max_results=0)

        with pytest.raises(Exception):  # Pydantic ValidationError
            Query(query_text="test", max_results=101)

    def test_query_json_serialization(self):
        """Test Query can be serialized to JSON."""
        query = Query(
            query_text="test query",
            intent=QueryIntent.FACTUAL,
            filters=QueryFilters(people=["Alice"]),
            max_results=15,
        )
        json_data = query.model_dump()
        assert json_data["query_text"] == "test query"
        assert json_data["intent"] == "factual"
        assert json_data["filters"]["people"] == ["Alice"]
        assert json_data["max_results"] == 15


class TestCitation:
    """Tests for Citation model."""

    def test_citation_minimal(self):
        """Test Citation with only memory_id."""
        citation = Citation(memory_id="mem_123")
        assert citation.memory_id == "mem_123"
        assert citation.title is None
        assert citation.created_at is None
        assert citation.excerpt is None

    def test_citation_complete(self):
        """Test Citation with all fields."""
        created = datetime(2025, 1, 15, tzinfo=timezone.utc)
        citation = Citation(
            memory_id="mem_456",
            title="Meeting Notes",
            created_at=created,
            excerpt="Discussed project timeline...",
        )
        assert citation.memory_id == "mem_456"
        assert citation.title == "Meeting Notes"
        assert citation.created_at == created
        assert citation.excerpt == "Discussed project timeline..."


class TestGroundedAnswer:
    """Tests for GroundedAnswer model."""

    def test_answer_minimal(self):
        """Test GroundedAnswer with minimal fields."""
        answer = GroundedAnswer(
            query="What did I do?", answer="I don't have enough information."
        )
        assert answer.query == "What did I do?"
        assert answer.answer == "I don't have enough information."
        assert answer.citations == []
        assert answer.confidence == 0.0
        assert answer.has_evidence is False
        assert answer.reasoning is None

    def test_answer_with_evidence(self):
        """Test GroundedAnswer with citations and evidence."""
        citations = [
            Citation(memory_id="mem_1", title="Note 1"),
            Citation(memory_id="mem_2", title="Note 2"),
        ]
        answer = GroundedAnswer(
            query="What meetings did I have?",
            answer="You had meetings with Alice [1] and Bob [2].",
            citations=citations,
            confidence=0.9,
            has_evidence=True,
            reasoning="Found 2 relevant meeting notes",
        )
        assert answer.query == "What meetings did I have?"
        assert "Alice [1]" in answer.answer
        assert len(answer.citations) == 2
        assert answer.confidence == 0.9
        assert answer.has_evidence is True
        assert "2 relevant" in answer.reasoning

    def test_answer_confidence_validation(self):
        """Test GroundedAnswer confidence bounds."""
        # Valid range
        answer = GroundedAnswer(
            query="test", answer="test", confidence=0.5, has_evidence=True
        )
        assert answer.confidence == 0.5

        # Test boundaries
        answer = GroundedAnswer(
            query="test", answer="test", confidence=0.0, has_evidence=False
        )
        assert answer.confidence == 0.0

        answer = GroundedAnswer(
            query="test", answer="test", confidence=1.0, has_evidence=True
        )
        assert answer.confidence == 1.0

        # Invalid values should raise validation error
        with pytest.raises(Exception):  # Pydantic ValidationError
            GroundedAnswer(
                query="test", answer="test", confidence=-0.1, has_evidence=False
            )

        with pytest.raises(Exception):  # Pydantic ValidationError
            GroundedAnswer(
                query="test", answer="test", confidence=1.1, has_evidence=True
            )

    def test_answer_zero_evidence_policy(self):
        """Test GroundedAnswer enforces zero-evidence policy."""
        # No citations = no evidence
        answer = GroundedAnswer(
            query="test",
            answer="I don't know",
            citations=[],
            has_evidence=False,
        )
        assert answer.has_evidence is False
        assert len(answer.citations) == 0

        # With citations = has evidence
        answer = GroundedAnswer(
            query="test",
            answer="Based on [1]...",
            citations=[Citation(memory_id="mem_1")],
            has_evidence=True,
        )
        assert answer.has_evidence is True
        assert len(answer.citations) > 0
