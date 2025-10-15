"""Tests for memory schemas."""

from datetime import datetime
from uuid import UUID

from app.memory.schemas import (
    ConversationMessage,
    MemoryItem,
    MemoryQuery,
    MemorySearchResult,
    MemorySection,
    MemorySource,
    MemoryStatus,
)


def test_memory_item_creation():
    """Test creating a basic memory item."""
    item = MemoryItem(
        source=MemorySource.CAPTURE,
        title="Test memory",
        content="This is a test memory",
    )

    assert isinstance(item.id, UUID)
    assert item.source == MemorySource.CAPTURE
    assert item.title == "Test memory"
    assert item.section == MemorySection.NOTE  # Default
    assert item.status == MemoryStatus.ACTIVE  # Default
    assert isinstance(item.created_at, datetime)


def test_memory_item_with_metadata():
    """Test creating a memory item with full metadata."""
    item = MemoryItem(
        source=MemorySource.DIARY,
        title="Meeting with team",
        content="Discussed project roadmap",
        section=MemorySection.EVENT,
        people=["Alice", "Bob"],
        tags=["work", "meeting"],
        location="Office",
        event_start_at=datetime(2025, 10, 15, 10, 0),
        timezone="Europe/Madrid",
        date_bucket="2025-10-15",
    )

    assert item.section == MemorySection.EVENT
    assert len(item.people) == 2
    assert "work" in item.tags
    assert item.location == "Office"
    assert item.event_start_at.hour == 10


def test_conversation_message_creation():
    """Test creating a conversation message."""
    msg = ConversationMessage(
        chat_id="123",
        role="user",
        content="Hello, bot!",
    )

    assert isinstance(msg.id, UUID)
    assert msg.chat_id == "123"
    assert msg.role == "user"
    assert msg.content == "Hello, bot!"
    assert isinstance(msg.timestamp, datetime)


def test_memory_query_defaults():
    """Test memory query with defaults."""
    query = MemoryQuery(query="search term")

    assert query.query == "search term"
    assert query.top_k == 4  # Default
    assert query.filters == {}
    assert query.section is None


def test_memory_query_with_filters():
    """Test memory query with filters."""
    query = MemoryQuery(
        query="find meetings",
        top_k=10,
        section=MemorySection.EVENT,
        people=["Alice"],
        tags=["work"],
        start_date=datetime(2025, 10, 1),
    )

    assert query.top_k == 10
    assert query.section == MemorySection.EVENT
    assert "Alice" in query.people
    assert "work" in query.tags


def test_memory_search_result():
    """Test memory search result."""
    item = MemoryItem(
        source=MemorySource.CAPTURE,
        title="Test",
        content="Content",
    )

    result = MemorySearchResult(
        item=item,
        score=0.95,
        highlights=["matching text"],
    )

    assert result.item.title == "Test"
    assert result.score == 0.95
    assert len(result.highlights) == 1


def test_memory_item_json_serialization():
    """Test that memory items can be serialized to JSON."""
    item = MemoryItem(
        source=MemorySource.CAPTURE,
        title="Test",
        content="Content",
        created_at=datetime(2025, 10, 15, 12, 0),
    )

    json_str = item.model_dump_json()
    assert "Test" in json_str
    assert "capture" in json_str

    # Deserialize
    item2 = MemoryItem.model_validate_json(json_str)
    assert item2.title == item.title
    assert item2.source == item.source
