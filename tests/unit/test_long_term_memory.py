"""Tests for long-term memory."""


import pytest

from app.memory.long_term import LongTermMemory
from app.memory.schemas import MemoryItem, MemoryQuery, MemorySection, MemorySource

# Skip tests if chromadb is not available
pytest.importorskip("chromadb")


@pytest.fixture
def ltm(test_data_dir, request):
    """Create a long-term memory instance for testing."""
    # Use test name and module for unique store per test
    test_name = request.node.name
    test_module = request.node.module.__name__.split('.')[-1]
    store_path = test_data_dir / f"{test_module}_{test_name}_chroma"
    return LongTermMemory(store_path=store_path)


@pytest.fixture
def sample_memory_item():
    """Create a sample memory item."""
    return MemoryItem(
        source=MemorySource.CAPTURE,
        title="Team meeting",
        content="Discussed Q4 planning and resource allocation",
        section=MemorySection.EVENT,
        people=["Alice", "Bob"],
        tags=["work", "planning"],
        date_bucket="2025-10-15",
    )


def test_ltm_initialization(ltm):
    """Test that LTM initializes correctly."""
    assert ltm.store_path.exists()
    assert ltm.collection is not None


def test_add_and_get_memory(ltm, sample_memory_item):
    """Test adding and retrieving a memory item."""
    ltm.add(sample_memory_item)

    retrieved = ltm.get(sample_memory_item.id)
    assert retrieved is not None
    assert retrieved.title == "Team meeting"
    assert retrieved.section == MemorySection.EVENT
    assert "Alice" in retrieved.people


def test_search_memories(ltm, sample_memory_item):
    """Test searching for memories."""
    ltm.add(sample_memory_item)

    # Add another item
    item2 = MemoryItem(
        source=MemorySource.CAPTURE,
        title="Lunch break",
        content="Had lunch at the new restaurant",
        section=MemorySection.NOTE,
    )
    ltm.add(item2)

    # Search for "meeting"
    query = MemoryQuery(query="meeting planning", top_k=5)
    results = ltm.search(query)

    assert len(results) > 0
    assert results[0].item.title in ["Team meeting", "Lunch break"]
    assert 0 <= results[0].score <= 1


def test_update_memory(ltm, sample_memory_item):
    """Test updating a memory item."""
    ltm.add(sample_memory_item)

    # Update the item
    sample_memory_item.title = "Updated: Team meeting"
    sample_memory_item.tags.append("updated")
    ltm.update(sample_memory_item)

    # Retrieve and verify
    retrieved = ltm.get(sample_memory_item.id)
    assert retrieved is not None
    assert retrieved.title == "Updated: Team meeting"
    assert "updated" in retrieved.tags


def test_delete_memory(ltm, sample_memory_item):
    """Test deleting a memory item."""
    ltm.add(sample_memory_item)

    ltm.delete(sample_memory_item.id)

    retrieved = ltm.get(sample_memory_item.id)
    assert retrieved is None


def test_count_memories(ltm):
    """Test counting memory items."""
    # Add items of different sections
    ltm.add(
        MemoryItem(
            source=MemorySource.CAPTURE,
            title="Note 1",
            content="Content",
            section=MemorySection.NOTE,
        )
    )
    ltm.add(
        MemoryItem(
            source=MemorySource.CAPTURE,
            title="Event 1",
            content="Content",
            section=MemorySection.EVENT,
        )
    )
    ltm.add(
        MemoryItem(
            source=MemorySource.CAPTURE,
            title="Note 2",
            content="Content",
            section=MemorySection.NOTE,
        )
    )

    total = ltm.count()
    assert total == 3

    notes = ltm.count(section=MemorySection.NOTE)
    assert notes == 2

    events = ltm.count(section=MemorySection.EVENT)
    assert events == 1


def test_search_with_section_filter(ltm):
    """Test searching with section filter."""
    ltm.add(
        MemoryItem(
            source=MemorySource.CAPTURE,
            title="Meeting notes",
            content="Important meeting",
            section=MemorySection.EVENT,
        )
    )
    ltm.add(
        MemoryItem(
            source=MemorySource.CAPTURE,
            title="Random note",
            content="Just a note about meetings",
            section=MemorySection.NOTE,
        )
    )

    # Search only in EVENT section
    query = MemoryQuery(query="meeting", section=MemorySection.EVENT, top_k=5)
    results = ltm.search(query)

    assert len(results) > 0
    # Should only return EVENT items
    for result in results:
        assert result.item.section == MemorySection.EVENT


def test_multiple_items_search_ranking(ltm):
    """Test that search results are ranked by relevance."""
    # Add items with varying relevance
    ltm.add(
        MemoryItem(
            source=MemorySource.CAPTURE,
            title="Python programming guide",
            content="Complete guide to Python programming with examples",
            section=MemorySection.NOTE,
        )
    )
    ltm.add(
        MemoryItem(
            source=MemorySource.CAPTURE,
            title="JavaScript basics",
            content="Introduction to JavaScript programming",
            section=MemorySection.NOTE,
        )
    )
    ltm.add(
        MemoryItem(
            source=MemorySource.CAPTURE,
            title="Grocery list",
            content="Buy milk and bread",
            section=MemorySection.LIST,
        )
    )

    # Search for "Python programming"
    query = MemoryQuery(query="Python programming", top_k=3)
    results = ltm.search(query)

    assert len(results) > 0
    # First result should be most relevant (Python guide)
    assert "Python" in results[0].item.title or "Python" in results[0].item.content
