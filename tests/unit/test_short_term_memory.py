"""Tests for short-term memory."""

from datetime import UTC, datetime, timedelta

import pytest

from app.memory.schemas import ConversationMessage
from app.memory.short_term import ShortTermMemory


@pytest.fixture
def stm(test_data_dir, request):
    """Create a short-term memory instance for testing."""
    # Use test name for unique DB per test
    test_name = request.node.name
    db_path = test_data_dir / f"{test_name}.sqlite"
    return ShortTermMemory(db_path=db_path, window_size=10, ttl_hours=24)


def test_stm_initialization(stm):
    """Test that STM initializes correctly."""
    assert stm.window_size == 10
    assert stm.ttl_hours == 24
    assert stm.db_path.exists()


def test_add_and_retrieve_message(stm):
    """Test adding and retrieving messages."""
    msg = ConversationMessage(
        chat_id="chat1",
        role="user",
        content="Hello!",
    )

    stm.add_message(msg)

    history = stm.get_history("chat1")
    assert len(history) == 1
    assert history[0].content == "Hello!"
    assert history[0].role == "user"


def test_multiple_messages(stm):
    """Test adding multiple messages."""
    messages = [
        ConversationMessage(chat_id="chat1", role="user", content="Message 1"),
        ConversationMessage(chat_id="chat1", role="assistant", content="Response 1"),
        ConversationMessage(chat_id="chat1", role="user", content="Message 2"),
    ]

    for msg in messages:
        stm.add_message(msg)

    history = stm.get_history("chat1")
    assert len(history) == 3
    # Should be newest first
    assert history[0].content == "Message 2"
    assert history[2].content == "Message 1"


def test_window_size_limit(stm):
    """Test that window size is enforced."""
    # Add 15 messages (window_size is 10)
    for i in range(15):
        msg = ConversationMessage(
            chat_id="chat1",
            role="user",
            content=f"Message {i}",
        )
        stm.add_message(msg)

    history = stm.get_history("chat1")
    assert len(history) == 10  # Only keep 10 most recent
    assert history[0].content == "Message 14"  # Newest
    assert history[9].content == "Message 5"  # Oldest kept


def test_multiple_chats(stm):
    """Test handling multiple separate chats."""
    stm.add_message(ConversationMessage(chat_id="chat1", role="user", content="Chat 1 msg"))
    stm.add_message(ConversationMessage(chat_id="chat2", role="user", content="Chat 2 msg"))

    history1 = stm.get_history("chat1")
    history2 = stm.get_history("chat2")

    assert len(history1) == 1
    assert len(history2) == 1
    assert history1[0].content == "Chat 1 msg"
    assert history2[0].content == "Chat 2 msg"


def test_clear_chat(stm):
    """Test clearing a chat's history."""
    stm.add_message(ConversationMessage(chat_id="chat1", role="user", content="Message 1"))
    stm.add_message(ConversationMessage(chat_id="chat1", role="user", content="Message 2"))

    deleted = stm.clear_chat("chat1")
    assert deleted == 2

    history = stm.get_history("chat1")
    assert len(history) == 0


def test_get_all_chats(stm):
    """Test getting all chat IDs."""
    stm.add_message(ConversationMessage(chat_id="chat1", role="user", content="Hi"))
    stm.add_message(ConversationMessage(chat_id="chat2", role="user", content="Hello"))
    stm.add_message(ConversationMessage(chat_id="chat3", role="user", content="Hey"))

    chats = stm.get_all_chats()
    assert len(chats) == 3
    assert "chat1" in chats
    assert "chat2" in chats
    assert "chat3" in chats


def test_message_count(stm):
    """Test getting message count for a chat."""
    for i in range(5):
        stm.add_message(ConversationMessage(chat_id="chat1", role="user", content=f"Msg {i}"))

    count = stm.get_message_count("chat1")
    assert count == 5


def test_history_with_limit(stm):
    """Test retrieving history with custom limit."""
    for i in range(10):
        stm.add_message(ConversationMessage(chat_id="chat1", role="user", content=f"Msg {i}"))

    history = stm.get_history("chat1", limit=3)
    assert len(history) == 3
    assert history[0].content == "Msg 9"  # Most recent


def test_history_with_since(stm):
    """Test retrieving history since a timestamp."""
    base_time = datetime.now(UTC)

    # Add older message
    old_msg = ConversationMessage(chat_id="chat1", role="user", content="Old")
    old_msg.timestamp = base_time - timedelta(hours=2)
    stm.add_message(old_msg)

    # Add newer message
    new_msg = ConversationMessage(chat_id="chat1", role="user", content="New")
    new_msg.timestamp = base_time
    stm.add_message(new_msg)

    # Get only messages after 1 hour ago
    since = base_time - timedelta(hours=1)
    history = stm.get_history("chat1", since=since)

    assert len(history) == 1
    assert history[0].content == "New"
