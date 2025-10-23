"""
Integration tests for Phase 3: Intelligent Clarification
Tests ambiguity detection, corrections, and cancel commands.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Message, Update, User, Chat

from app.adapters.telegram import VitaeBot
from app.adapters.conversation_session import ConversationState
from app.config import Settings
from app.llm.service import LLMService
from app.memory import MemoryService
from app.tools.registry import ToolRegistry


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock(spec=Settings)
    settings.telegram_token = "test_token"
    settings.llm_model = "qwen3:1.7b"
    settings.llm_timeout = 30
    return settings


@pytest.fixture
def mock_llm_service():
    """Create mock LLM service."""
    return MagicMock(spec=LLMService)


@pytest.fixture
def mock_memory_service():
    """Create mock memory service."""
    memory = MagicMock(spec=MemoryService)
    memory.stm = MagicMock()
    memory.stm.get_history = MagicMock(return_value=[])
    memory.ltm = MagicMock()
    return memory


@pytest.fixture
def mock_tool_registry():
    """Create mock tool registry."""
    return MagicMock(spec=ToolRegistry)


@pytest.fixture
def vitae_bot(mock_settings, mock_memory_service, mock_tool_registry, mock_llm_service):
    """Create VitaeBot instance with mocks."""
    return VitaeBot(
        settings=mock_settings,
        memory_service=mock_memory_service,
        tool_registry=mock_tool_registry,
        llm_service=mock_llm_service,
    )


@pytest.fixture
def mock_update():
    """Create mock Telegram update."""
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 12345
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 67890
    update.effective_user.first_name = "Test User"
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    return update


@pytest.mark.asyncio
async def test_cancel_command_during_enrichment(vitae_bot, mock_update):
    """Test that cancel command aborts the conversation at any stage."""
    # Start conversation
    mock_update.message.text = "Met someone"
    
    with patch.object(vitae_bot.router, 'route') as mock_route:
        mock_route.return_value = MagicMock(
            intent=MagicMock(value="note_taking"),
            confidence=0.9,
            requires_action=True,
            target_crew="capture",
            extracted_entities={"title": "Met someone", "content": "Met someone"},
            conversational_response="Got it!"
        )
        
        # First message - should trigger enrichment
        with patch.object(vitae_bot.enricher, 'needs_enrichment', return_value=True):
            with patch.object(vitae_bot.enricher, 'generate_follow_up_questions', return_value="Who did you meet?"):
                await vitae_bot.handle_message(mock_update, None)
    
    # Get session
    user_id = str(mock_update.effective_user.id)
    chat_id = str(mock_update.effective_chat.id)
    session = vitae_bot.session_manager.get_session(user_id, chat_id)
    
    # Verify we're in enrichment state
    assert session.state == ConversationState.GATHERING_DETAILS
    
    # Send cancel command
    mock_update.message.text = "cancel"
    await vitae_bot.handle_message(mock_update, None)
    
    # Verify session was reset
    session = vitae_bot.session_manager.get_session(user_id, chat_id)
    assert session.state == ConversationState.INITIAL
    
    # Verify user got feedback
    assert any("Cancelled" in str(call) or "cancelled" in str(call) 
              for call in mock_update.message.reply_text.call_args_list)


@pytest.mark.asyncio
async def test_correction_during_enrichment(vitae_bot, mock_update):
    """Test that user can correct their previous answer."""
    # Start conversation
    mock_update.message.text = "Met someone"
    
    with patch.object(vitae_bot.router, 'route') as mock_route:
        mock_route.return_value = MagicMock(
            intent=MagicMock(value="note_taking"),
            confidence=0.9,
            requires_action=True,
            target_crew="capture",
            extracted_entities={"title": "Met someone", "content": "Met someone"},
            conversational_response="Got it!"
        )
        
        # First message - trigger enrichment
        with patch.object(vitae_bot.enricher, 'needs_enrichment', return_value=True):
            with patch.object(vitae_bot.enricher, 'generate_follow_up_questions', return_value="Who did you meet?"):
                await vitae_bot.handle_message(mock_update, None)
    
    # User answers
    mock_update.message.text = "Bob"
    
    with patch.object(vitae_bot.enricher, 'extract_info_from_response') as mock_extract:
        mock_extract.return_value = {"title": "Met someone", "content": "Met someone\nBob", "people": ["Bob"]}
        
        with patch.object(vitae_bot.enricher, 'needs_enrichment', return_value=False):
            # This will trigger _show_confirmation_preview
            await vitae_bot.handle_message(mock_update, None)
    
    # Get session
    user_id = str(mock_update.effective_user.id)
    chat_id = str(mock_update.effective_chat.id)
    session = vitae_bot.session_manager.get_session(user_id, chat_id)
    
    # Verify we moved to confirmation
    assert session.state == ConversationState.AWAITING_CONFIRMATION
    
    # Now user corrects: "No, I meant Alice"
    mock_update.message.text = "No, I meant Alice"
    
    with patch.object(vitae_bot.correction_handler, 'apply_correction') as mock_correct:
        mock_correct.return_value = {
            "title": "Met someone",
            "content": "Met someone\nAlice",
            "people": ["Alice"],
            "follow_up_responses": ["[CORRECTION] No, I meant Alice"]
        }
        
        await vitae_bot.handle_message(mock_update, None)
    
    # Verify correction was applied
    assert mock_correct.called
    
    # Verify user got feedback
    assert any("updated" in str(call).lower() or "got it" in str(call).lower()
              for call in mock_update.message.reply_text.call_args_list)


@pytest.mark.asyncio
async def test_ambiguity_detection_simple(vitae_bot, mock_update):
    """Test ambiguity detection for simple ambiguous statement."""
    mock_update.message.text = "lunch tomorrow"
    
    with patch.object(vitae_bot.router, 'route') as mock_route:
        mock_route.return_value = MagicMock(
            intent=MagicMock(value="note_taking"),
            confidence=0.7,  # Lower confidence due to ambiguity
            requires_action=True,
            target_crew="capture",
            extracted_entities={"title": "lunch tomorrow", "content": "lunch tomorrow"},
            conversational_response="Okay!"
        )
        
        # Mock ambiguity detection
        with patch.object(vitae_bot.clarification_detector, 'detect_ambiguity') as mock_detect:
            mock_detect.return_value = {
                'type': 'ambiguous_intent',
                'question': 'What do you mean by "lunch tomorrow"?',
                'options': [
                    {'label': 'Save note', 'interpretation': 'You had/will have lunch tomorrow', 'intent': 'note_taking'},
                    {'label': 'Create task', 'interpretation': 'Remind you about lunch tomorrow', 'intent': 'task_create'}
                ],
                'confidence': 0.8
            }
            
            await vitae_bot.handle_message(mock_update, None)
    
    # Get session
    user_id = str(mock_update.effective_user.id)
    chat_id = str(mock_update.effective_chat.id)
    session = vitae_bot.session_manager.get_session(user_id, chat_id)
    
    # Verify we entered clarifying state
    assert session.state == ConversationState.CLARIFYING
    assert len(session.clarification_options) == 2
    
    # Verify user was asked for clarification
    last_reply = str(mock_update.message.reply_text.call_args_list[-1])
    assert "1." in last_reply and "2." in last_reply


@pytest.mark.asyncio
async def test_clarification_response_with_number(vitae_bot, mock_update):
    """Test user responds to clarification with option number."""
    # Set up session in clarifying state
    user_id = str(mock_update.effective_user.id)
    chat_id = str(mock_update.effective_chat.id)
    session = vitae_bot.session_manager.get_session(user_id, chat_id)
    
    session.state = ConversationState.CLARIFYING
    session.intent = "note_taking"
    session.original_message = "lunch tomorrow"
    session.collected_data = {"title": "lunch tomorrow", "content": "lunch tomorrow"}
    session.clarification_options = [
        {'label': 'Save note', 'interpretation': 'You had/will have lunch tomorrow', 'intent': 'note_taking'},
        {'label': 'Create task', 'interpretation': 'Remind you about lunch tomorrow', 'intent': 'task_create'}
    ]
    session.last_question = 'What do you mean by "lunch tomorrow"?'
    
    # User selects option 1
    mock_update.message.text = "1"
    
    with patch.object(vitae_bot.enricher, 'needs_enrichment', return_value=False):
        await vitae_bot.handle_message(mock_update, None)
    
    # Verify we moved to confirmation
    session = vitae_bot.session_manager.get_session(user_id, chat_id)
    assert session.state == ConversationState.AWAITING_CONFIRMATION
    
    # Verify clarification options were cleared
    assert len(session.clarification_options) == 0


@pytest.mark.asyncio
async def test_cancel_when_no_active_session(vitae_bot, mock_update):
    """Test cancel command when there's no active session."""
    mock_update.message.text = "cancel"
    
    await vitae_bot.handle_message(mock_update, None)
    
    # Verify user got appropriate message
    last_reply = str(mock_update.message.reply_text.call_args_list[-1])
    assert "nothing to cancel" in last_reply.lower()


@pytest.mark.asyncio
async def test_correction_patterns_detection(vitae_bot, mock_update):
    """Test various correction phrase patterns are detected."""
    correction_phrases = [
        "no, I meant Alice",
        "No, that's not what I meant",
        "Actually, it was Bob",
        "Let me clarify - it was Carol",
        "no quiero decir eso",  # Spanish
        "en realidad fue Dave"  # Spanish
    ]
    
    for phrase in correction_phrases:
        is_correction = vitae_bot.clarification_detector.is_correction(phrase)
        assert is_correction, f"Failed to detect correction in: {phrase}"


@pytest.mark.asyncio
async def test_cancel_patterns_detection(vitae_bot, mock_update):
    """Test various cancel phrase patterns are detected."""
    cancel_phrases = [
        "cancel",
        "stop",
        "forget it",
        "never mind",
        "cancelar",  # Spanish
        "olvídalo"  # Spanish
    ]
    
    for phrase in cancel_phrases:
        is_cancel = vitae_bot.clarification_detector.is_cancel_command(phrase)
        assert is_cancel, f"Failed to detect cancel in: {phrase}"


@pytest.mark.asyncio
async def test_full_flow_with_correction_and_confirmation(vitae_bot, mock_update):
    """Test complete flow: enrichment → correction → confirmation → execution."""
    # Step 1: Initial message
    mock_update.message.text = "Met someone"
    
    with patch.object(vitae_bot.router, 'route') as mock_route:
        mock_route.return_value = MagicMock(
            intent=MagicMock(value="note_taking"),
            confidence=0.9,
            requires_action=True,
            target_crew="capture",
            extracted_entities={"title": "Met someone", "content": "Met someone"},
            conversational_response="Got it!"
        )
        
        with patch.object(vitae_bot.enricher, 'needs_enrichment', return_value=True):
            with patch.object(vitae_bot.enricher, 'generate_follow_up_questions', return_value="Who did you meet?"):
                await vitae_bot.handle_message(mock_update, None)
    
    # Step 2: Answer follow-up
    mock_update.message.text = "Bob"
    
    with patch.object(vitae_bot.enricher, 'extract_info_from_response') as mock_extract:
        mock_extract.return_value = {
            "title": "Met someone",
            "content": "Met someone\nBob",
            "people": ["Bob"],
            "places": [],
            "tags": []
        }
        
        with patch.object(vitae_bot.enricher, 'needs_enrichment', return_value=False):
            await vitae_bot.handle_message(mock_update, None)
    
    user_id = str(mock_update.effective_user.id)
    chat_id = str(mock_update.effective_chat.id)
    session = vitae_bot.session_manager.get_session(user_id, chat_id)
    assert session.state == ConversationState.AWAITING_CONFIRMATION
    
    # Step 3: Correction
    mock_update.message.text = "No, I meant Alice"
    
    with patch.object(vitae_bot.correction_handler, 'apply_correction') as mock_correct:
        mock_correct.return_value = {
            "title": "Met someone",
            "content": "Met someone\nAlice",
            "people": ["Alice"],
            "places": [],
            "tags": [],
            "follow_up_responses": ["Bob", "[CORRECTION] No, I meant Alice"]
        }
        
        # This should not change state, just update data and re-show confirmation
        await vitae_bot.handle_message(mock_update, None)
    
    # Should still be in confirmation state (note: correction during confirmation goes back to preview)
    session = vitae_bot.session_manager.get_session(user_id, chat_id)
    # Correction handler doesn't change state during confirmation - it re-shows preview
    assert session.state == ConversationState.AWAITING_CONFIRMATION
    
    # Step 4: Confirm
    mock_update.message.text = "yes"
    
    with patch.object(vitae_bot.capture_crew, 'capture') as mock_capture:
        mock_capture.return_value = MagicMock(
            success=True,
            message="Note saved successfully",
            actions_executed=1,
            summary="Saved note"
        )
        
        await vitae_bot.handle_message(mock_update, None)
    
    # Verify execution happened
    assert mock_capture.called
    
    # Verify session was reset
    session = vitae_bot.session_manager.get_session(user_id, chat_id)
    assert session.state == ConversationState.INITIAL
