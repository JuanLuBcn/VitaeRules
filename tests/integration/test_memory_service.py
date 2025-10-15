"""Integration tests for the unified memory service."""


import pytest

from app.memory import (
    MemoryItem,
    MemoryQuery,
    MemorySection,
    MemoryService,
    MemorySource,
)
from app.memory.long_term import LongTermMemory
from app.memory.short_term import ShortTermMemory

# Skip tests if chromadb is not available
pytest.importorskip("chromadb")


@pytest.fixture
def memory_service(test_data_dir, request):
    """Create a memory service for testing."""
    # Use test name and module for unique stores per test
    test_name = request.node.name
    test_module = request.node.module.__name__.split('.')[-1]
    stm = ShortTermMemory(db_path=test_data_dir / f"{test_module}_{test_name}.sqlite")
    ltm = LongTermMemory(store_path=test_data_dir / f"{test_module}_{test_name}_chroma")
    return MemoryService(stm=stm, ltm=ltm)


def test_add_and_retrieve_conversation(memory_service):
    """Test adding and retrieving conversation messages."""
    # Add messages
    memory_service.add_message(
        chat_id="chat1",
        role="user",
        content="Hello, assistant!",
        user_id="user1",
    )

    memory_service.add_message(
        chat_id="chat1",
        role="assistant",
        content="Hello! How can I help you?",
    )

    # Retrieve history
    history = memory_service.get_conversation_history("chat1")

    assert len(history) == 2
    assert history[0].role == "assistant"  # Newest first
    assert history[1].role == "user"


def test_save_and_search_memory(memory_service):
    """Test saving and searching memory items."""
    # Create and save a memory
    item = MemoryItem(
        source=MemorySource.CAPTURE,
        title="Project kickoff meeting",
        content="Discussed project scope, timeline, and team assignments",
        section=MemorySection.EVENT,
        people=["Alice", "Bob", "Charlie"],
        tags=["project", "meeting"],
        chat_id="chat1",
        user_id="user1",
    )

    saved = memory_service.save_memory(item)
    assert saved.id == item.id

    # Search for it
    query = MemoryQuery(query="project meeting", top_k=5)
    results = memory_service.search_memories(query)

    assert len(results) > 0
    assert results[0].item.title == "Project kickoff meeting"


def test_get_memory_by_id(memory_service):
    """Test retrieving a specific memory by ID."""
    # Save a memory
    item = MemoryItem(
        source=MemorySource.CAPTURE,
        title="Important note",
        content="Remember to review the documentation",
    )

    memory_service.save_memory(item)

    # Retrieve by ID
    retrieved = memory_service.get_memory(item.id)

    assert retrieved is not None
    assert retrieved.id == item.id
    assert retrieved.title == "Important note"


def test_update_memory(memory_service):
    """Test updating a memory item."""
    # Save original
    item = MemoryItem(
        source=MemorySource.CAPTURE,
        title="Original title",
        content="Original content",
    )

    memory_service.save_memory(item)

    # Update
    item.title = "Updated title"
    item.content = "Updated content"
    memory_service.update_memory(item)

    # Retrieve and verify
    retrieved = memory_service.get_memory(item.id)
    assert retrieved.title == "Updated title"
    assert retrieved.content == "Updated content"


def test_delete_memory(memory_service):
    """Test deleting a memory item."""
    # Save a memory
    item = MemoryItem(
        source=MemorySource.CAPTURE,
        title="To be deleted",
        content="This will be deleted",
    )

    memory_service.save_memory(item)

    # Delete
    memory_service.delete_memory(item.id)

    # Verify deletion
    retrieved = memory_service.get_memory(item.id)
    assert retrieved is None


def test_create_note_convenience(memory_service):
    """Test the convenience method for creating notes."""
    note = memory_service.create_note(
        title="Quick note",
        content="This is a quick note",
        chat_id="chat1",
        user_id="user1",
        tags=["quick", "test"],
    )

    assert note.title == "Quick note"
    assert note.section == MemorySection.NOTE
    assert note.source == MemorySource.CAPTURE
    assert "quick" in note.tags

    # Verify it's saved
    retrieved = memory_service.get_memory(note.id)
    assert retrieved is not None


def test_get_recent_context(memory_service):
    """Test getting formatted recent context."""
    # Add some messages
    memory_service.add_message(chat_id="chat1", role="user", content="What's the weather?")
    memory_service.add_message(chat_id="chat1", role="assistant", content="It's sunny!")
    memory_service.add_message(chat_id="chat1", role="user", content="Great!")

    context = memory_service.get_recent_context("chat1", message_limit=10)

    assert "user: What's the weather?" in context
    assert "assistant: It's sunny!" in context
    assert "user: Great!" in context


def test_count_memories(memory_service):
    """Test counting memories by section."""
    # Add different types
    memory_service.save_memory(
        MemoryItem(
            source=MemorySource.CAPTURE,
            title="Note 1",
            content="Content",
            section=MemorySection.NOTE,
        )
    )
    memory_service.save_memory(
        MemoryItem(
            source=MemorySource.CAPTURE,
            title="Event 1",
            content="Content",
            section=MemorySection.EVENT,
        )
    )
    memory_service.save_memory(
        MemoryItem(
            source=MemorySource.CAPTURE,
            title="Note 2",
            content="Content",
            section=MemorySection.NOTE,
        )
    )

    total = memory_service.count_memories()
    assert total == 3

    notes = memory_service.count_memories(section=MemorySection.NOTE)
    assert notes == 2


def test_clear_conversation(memory_service):
    """Test clearing a conversation."""
    # Add messages
    for i in range(5):
        memory_service.add_message(chat_id="chat1", role="user", content=f"Message {i}")

    # Clear
    deleted = memory_service.clear_conversation("chat1")
    assert deleted == 5

    # Verify empty
    history = memory_service.get_conversation_history("chat1")
    assert len(history) == 0


def test_stm_and_ltm_isolation(memory_service):
    """Test that STM and LTM operate independently."""
    # Add to STM
    memory_service.add_message(chat_id="chat1", role="user", content="STM message")

    # Add to LTM
    memory_service.save_memory(
        MemoryItem(
            source=MemorySource.CAPTURE,
            title="LTM item",
            content="Long-term memory",
        )
    )

    # Verify STM
    history = memory_service.get_conversation_history("chat1")
    assert len(history) == 1
    assert history[0].content == "STM message"

    # Verify LTM
    results = memory_service.search_memories(MemoryQuery(query="long-term", top_k=5))
    assert len(results) > 0
    assert results[0].item.title == "LTM item"
