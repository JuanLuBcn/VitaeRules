"""Integration tests for Telegram bot note-taking and retrieval."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.adapters.telegram import VitaeBot
from app.config import get_settings
from app.memory import MemoryService
from app.tools.registry import ToolRegistry
from app.tools.task_tool import TaskTool
from app.tools.list_tool import ListTool
from app.tools.temporal_tool import TemporalTool
from app.tools.memory_note_tool import MemoryNoteTool
from app.llm import LLMService


@pytest.fixture
def memory_service():
    """Create a memory service for testing."""
    return MemoryService()


@pytest.fixture
def tool_registry(memory_service):
    """Create and populate tool registry."""
    registry = ToolRegistry()
    registry.register(TaskTool())
    registry.register(ListTool())
    registry.register(TemporalTool())
    registry.register(MemoryNoteTool(memory_service=memory_service))
    return registry


@pytest.fixture
def llm_service():
    """Create LLM service for testing."""
    return LLMService()


@pytest.fixture
def telegram_bot(memory_service, tool_registry, llm_service):
    """Create VitaeBot instance for testing."""
    settings = get_settings()
    return VitaeBot(
        settings=settings,
        memory_service=memory_service,
        tool_registry=tool_registry,
        llm_service=llm_service,
    )


@pytest.fixture
def mock_update():
    """Create a mock Telegram Update object."""
    update = MagicMock()
    update.effective_chat.id = 12345
    update.effective_user.id = 67890
    update.message = MagicMock()
    update.message.text = "Test message"
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create a mock Telegram Context object."""
    return MagicMock()


class TestNoteTaking:
    """Test note-taking functionality."""

    @pytest.mark.asyncio
    async def test_simple_note_capture(self, telegram_bot, mock_update, mock_context):
        """Test capturing a simple note with confirmation flow."""
        mock_update.message.text = "I had lunch with Alice today"
        mock_update.effective_user.first_name = "TestUser"
        
        # Mock the LLM router to return note_taking intent
        with patch.object(telegram_bot.router, 'route') as mock_route:
            from app.llm.router import RoutingDecision, ConversationIntent
            
            mock_route.return_value = RoutingDecision(
                intent=ConversationIntent.NOTE_TAKING,
                confidence=0.9,
                conversational_response="That sounds interesting! I've saved that.",
                extracted_entities={
                    "title": "Lunch with Alice",
                    "content": "Had lunch with Alice today",
                    "people": ["Alice"],
                    "tags": ["lunch", "social"],
                },
                reasoning="User is sharing a personal memory",
                requires_action=True,
                target_crew="capture",
            )
            
            # Mock the capture crew
            with patch.object(telegram_bot.capture_crew, 'capture') as mock_capture:
                from app.crews.capture.crew import CaptureResult
                from app.contracts.plan import Plan, SafetyCheck
                
                mock_capture.return_value = CaptureResult(
                    plan=Plan(
                        intent="memory.note",
                        confidence=0.9,
                        followups=[],
                        actions=[],
                        safety=SafetyCheck(blocked=False),
                    ),
                    results=[],
                    summary="Note saved successfully",
                    clarifications_asked=0,
                    actions_executed=1,
                )
                
                # STEP 1: Send initial message - should get confirmation request
                await telegram_bot.handle_message(mock_update, mock_context)
                
                # Verify conversational response was sent
                assert mock_update.message.reply_text.call_count >= 1
                first_call = mock_update.message.reply_text.call_args_list[0]
                assert "interesting" in first_call[0][0].lower() or "saved" in first_call[0][0].lower()
                
                # Verify we got a confirmation prompt
                last_call = mock_update.message.reply_text.call_args_list[-1]
                last_message = last_call[0][0].lower()
                assert "should i save" in last_message or "proceed" in last_message or "yes" in last_message
                
                # Capture should NOT be called yet (waiting for confirmation)
                assert mock_capture.call_count == 0
                
                # STEP 2: User confirms with "yes"
                mock_update.message.text = "yes"
                await telegram_bot.handle_message(mock_update, mock_context)
                
                # Now capture crew should have been called
                mock_capture.assert_called_once()
                call_args = mock_capture.call_args
                assert call_args[1]['user_input'] == "I had lunch with Alice today"

    @pytest.mark.asyncio
    async def test_note_with_location(self, telegram_bot, mock_update, mock_context):
        """Test capturing a note with location and confirmation flow."""
        mock_update.message.text = "Visited the Eiffel Tower in Paris"
        mock_update.effective_user.first_name = "TestUser"
        
        with patch.object(telegram_bot.router, 'route') as mock_route:
            from app.llm.router import RoutingDecision, ConversationIntent
            
            mock_route.return_value = RoutingDecision(
                intent=ConversationIntent.NOTE_TAKING,
                confidence=0.95,
                conversational_response="That sounds exciting! I've saved that memory.",
                extracted_entities={
                    "title": "Visited Eiffel Tower",
                    "content": "Visited the Eiffel Tower in Paris",
                    "places": ["Eiffel Tower", "Paris"],
                    "tags": ["travel", "sightseeing"],
                },
                reasoning="User sharing travel experience",
                requires_action=True,
                target_crew="capture",
            )
            
            with patch.object(telegram_bot.capture_crew, 'capture') as mock_capture:
                from app.crews.capture.crew import CaptureResult
                from app.contracts.plan import Plan, SafetyCheck
                
                mock_capture.return_value = CaptureResult(
                    plan=Plan(intent="memory.note", confidence=0.95, followups=[], actions=[], safety=SafetyCheck(blocked=False)),
                    results=[],
                    summary="Memory saved",
                    clarifications_asked=0,
                    actions_executed=1,
                )
                
                # STEP 1: Initial message - get confirmation prompt
                await telegram_bot.handle_message(mock_update, mock_context)
                
                # Verify response mentions excitement
                assert mock_update.message.reply_text.called
                
                # Should not have called capture yet
                assert mock_capture.call_count == 0
                
                # STEP 2: User confirms
                mock_update.message.text = "si"  # Test Spanish affirmative
                await telegram_bot.handle_message(mock_update, mock_context)
                
                # Now capture should be called
                mock_capture.assert_called_once()

    @pytest.mark.asyncio
    async def test_note_with_people_and_date(self, telegram_bot, mock_update, mock_context):
        """Test capturing a note with people and date information with confirmation flow."""
        mock_update.message.text = "Met with Bob and Carol yesterday to discuss the project"
        mock_update.effective_user.first_name = "TestUser"
        
        with patch.object(telegram_bot.router, 'route') as mock_route:
            from app.llm.router import RoutingDecision, ConversationIntent
            
            mock_route.return_value = RoutingDecision(
                intent=ConversationIntent.NOTE_TAKING,
                confidence=0.9,
                conversational_response="I've noted that meeting with Bob and Carol.",
                extracted_entities={
                    "title": "Meeting with Bob and Carol",
                    "content": "Met with Bob and Carol yesterday to discuss the project",
                    "people": ["Bob", "Carol"],
                    "tags": ["meeting", "project"],
                    "temporal": "yesterday",
                },
                reasoning="User recording a meeting",
                requires_action=True,
                target_crew="capture",
            )
            
            with patch.object(telegram_bot.capture_crew, 'capture') as mock_capture:
                from app.crews.capture.crew import CaptureResult
                from app.contracts.plan import Plan, SafetyCheck
                
                mock_capture.return_value = CaptureResult(
                    plan=Plan(intent="memory.note", confidence=0.9, followups=[], actions=[], safety=SafetyCheck(blocked=False)),
                    results=[],
                    summary="Meeting note saved",
                    clarifications_asked=0,
                    actions_executed=1,
                )
                
                # STEP 1: Initial message
                await telegram_bot.handle_message(mock_update, mock_context)
                
                # Should ask for confirmation, not execute yet
                assert mock_capture.call_count == 0
                
                # STEP 2: Confirm
                mock_update.message.text = "yes"
                await telegram_bot.handle_message(mock_update, mock_context)
                
                # Now should be called
                mock_capture.assert_called_once()


class TestRetrieval:
    """Test memory retrieval functionality."""

    @pytest.mark.asyncio
    async def test_simple_question(self, telegram_bot, mock_update, mock_context):
        """Test asking a simple question about memories."""
        mock_update.message.text = "What did I do with Alice?"
        
        with patch.object(telegram_bot.router, 'route') as mock_route:
            from app.llm.router import RoutingDecision, ConversationIntent
            
            mock_route.return_value = RoutingDecision(
                intent=ConversationIntent.QUESTION,
                confidence=0.9,
                conversational_response="Let me search my memory for that...",
                extracted_entities={
                    "query": "activities with Alice",
                    "people": ["Alice"],
                },
                reasoning="User asking about past activities",
                requires_action=True,
                target_crew="retrieval",
            )
            
            with patch.object(telegram_bot.retrieval_crew, 'retrieve') as mock_retrieve:
                from app.crews.retrieval.crew import RetrievalResult
                from app.contracts.query import Query, QueryIntent, GroundedAnswer
                
                mock_retrieve.return_value = RetrievalResult(
                    query=Query(
                        query_text="What did I do with Alice?",
                        intent=QueryIntent.FACTUAL,
                    ),
                    memories=[],
                    answer=GroundedAnswer(
                        query="What did I do with Alice?",
                        answer="You had lunch with Alice today.",
                        confidence=0.85,
                        citations=[],
                        has_evidence=True,
                        reasoning="Found memory about lunch with Alice",
                    ),
                )
                
                await telegram_bot.handle_message(mock_update, mock_context)
                
                # Verify conversational response was sent first
                assert mock_update.message.reply_text.call_count >= 2
                
                # Verify retrieval crew was called
                mock_retrieve.assert_called_once()
                call_args = mock_retrieve.call_args
                assert call_args[1]['user_question'] == "What did I do with Alice?"

    @pytest.mark.asyncio
    async def test_question_about_location(self, telegram_bot, mock_update, mock_context):
        """Test asking about a specific location."""
        mock_update.message.text = "When did I visit Paris?"
        
        with patch.object(telegram_bot.router, 'route') as mock_route:
            from app.llm.router import RoutingDecision, ConversationIntent
            
            mock_route.return_value = RoutingDecision(
                intent=ConversationIntent.QUESTION,
                confidence=0.95,
                conversational_response="Let me check when you visited Paris...",
                extracted_entities={
                    "query": "visit to Paris",
                    "places": ["Paris"],
                    "temporal": "when",
                },
                reasoning="User asking about travel date",
                requires_action=True,
                target_crew="retrieval",
            )
            
            with patch.object(telegram_bot.retrieval_crew, 'retrieve') as mock_retrieve:
                from app.crews.retrieval.crew import RetrievalResult
                from app.contracts.query import Query, QueryIntent, GroundedAnswer, Citation
                from datetime import datetime
                
                mock_retrieve.return_value = RetrievalResult(
                    query=Query(
                        query_text="When did I visit Paris?",
                        intent=QueryIntent.TEMPORAL,
                    ),
                    memories=[],
                    answer=GroundedAnswer(
                        query="When did I visit Paris?",
                        answer="You visited Paris and the Eiffel Tower recently.",
                        confidence=0.9,
                        citations=[
                            Citation(
                                memory_id="mem_123",
                                title="Visited Eiffel Tower",
                                created_at=datetime.now(),
                                excerpt="Visited the Eiffel Tower in Paris",
                            )
                        ],
                        has_evidence=True,
                        reasoning="Found travel memory",
                    ),
                )
                
                await telegram_bot.handle_message(mock_update, mock_context)
                
                # Verify response includes the answer
                assert mock_update.message.reply_text.call_count >= 2
                mock_retrieve.assert_called_once()

    @pytest.mark.asyncio
    async def test_question_no_results(self, telegram_bot, mock_update, mock_context):
        """Test asking a question when no memories are found."""
        mock_update.message.text = "What did I do with Zorro?"
        
        with patch.object(telegram_bot.router, 'route') as mock_route:
            from app.llm.router import RoutingDecision, ConversationIntent
            
            mock_route.return_value = RoutingDecision(
                intent=ConversationIntent.QUESTION,
                confidence=0.8,
                conversational_response="Let me search for that...",
                extracted_entities={
                    "query": "activities with Zorro",
                    "people": ["Zorro"],
                },
                reasoning="User asking about memories",
                requires_action=True,
                target_crew="retrieval",
            )
            
            with patch.object(telegram_bot.retrieval_crew, 'retrieve') as mock_retrieve:
                from app.crews.retrieval.crew import RetrievalResult
                from app.contracts.query import Query, QueryIntent, GroundedAnswer
                
                mock_retrieve.return_value = RetrievalResult(
                    query=Query(
                        query_text="What did I do with Zorro?",
                        intent=QueryIntent.FACTUAL,
                    ),
                    memories=[],
                    answer=GroundedAnswer(
                        query="What did I do with Zorro?",
                        answer="I couldn't find any memories about Zorro.",
                        confidence=0.2,
                        citations=[],
                        has_evidence=False,
                        reasoning="No relevant memories found",
                    ),
                )
                
                await telegram_bot.handle_message(mock_update, mock_context)
                
                # Verify low confidence is handled
                assert mock_update.message.reply_text.called
                mock_retrieve.assert_called_once()


class TestErrorHandling:
    """Test error handling in Telegram bot."""

    @pytest.mark.asyncio
    async def test_routing_error_fallback(self, telegram_bot, mock_update, mock_context):
        """Test fallback when routing fails."""
        mock_update.message.text = "Some ambiguous message"
        
        with patch.object(telegram_bot.router, 'route') as mock_route:
            mock_route.side_effect = Exception("LLM connection error")
            
            await telegram_bot.handle_message(mock_update, mock_context)
            
            # Verify error message was sent
            assert mock_update.message.reply_text.called
            call_args = mock_update.message.reply_text.call_args
            assert "error" in call_args[0][0].lower() or "try" in call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_capture_error_handling(self, telegram_bot, mock_update, mock_context):
        """Test error handling when capture fails."""
        mock_update.message.text = "I had a great meeting today at the office with the team to discuss our quarterly goals"
        mock_update.effective_user.first_name = "TestUser"
        
        with patch.object(telegram_bot.router, 'route') as mock_route:
            from app.llm.router import RoutingDecision, ConversationIntent
            
            mock_route.return_value = RoutingDecision(
                intent=ConversationIntent.NOTE_TAKING,
                confidence=0.9,
                conversational_response="I'll save that!",
                extracted_entities={
                    "title": "Great meeting",
                    "content": "Had a great meeting today at the office with the team to discuss our quarterly goals",
                    "people": ["team"],
                    "places": ["office"],
                    "tags": ["meeting", "work"]
                },
                reasoning="Note capture",
                requires_action=True,
                target_crew="capture",
            )
            
            with patch.object(telegram_bot.capture_crew, 'capture') as mock_capture:
                mock_capture.side_effect = Exception("Database error")
                
                # STEP 1: Initial message - should show confirmation (no enrichment due to complete data)
                await telegram_bot.handle_message(mock_update, mock_context)
                
                # Should show confirmation preview (not error yet)
                assert mock_update.message.reply_text.call_count >= 2
                last_call = mock_update.message.reply_text.call_args_list[-1]
                last_message = last_call[0][0].lower()
                assert "should i save" in last_message or "proceed" in last_message
                
                # STEP 2: User confirms - NOW error should occur
                mock_update.message.text = "yes"
                await telegram_bot.handle_message(mock_update, mock_context)
                
                # Verify error message was sent
                last_call = mock_update.message.reply_text.call_args_list[-1]
                assert "trouble" in last_call[0][0].lower() or "error" in last_call[0][0].lower()

    @pytest.mark.asyncio
    async def test_retrieval_error_handling(self, telegram_bot, mock_update, mock_context):
        """Test error handling when retrieval fails."""
        mock_update.message.text = "What did I do yesterday?"
        
        with patch.object(telegram_bot.router, 'route') as mock_route:
            from app.llm.router import RoutingDecision, ConversationIntent
            
            mock_route.return_value = RoutingDecision(
                intent=ConversationIntent.QUESTION,
                confidence=0.9,
                conversational_response="Let me check...",
                extracted_entities={},
                reasoning="Memory query",
                requires_action=True,
                target_crew="retrieval",
            )
            
            with patch.object(telegram_bot.retrieval_crew, 'retrieve') as mock_retrieve:
                mock_retrieve.side_effect = Exception("Search error")
                
                await telegram_bot.handle_message(mock_update, mock_context)
                
                # Verify error message was sent
                assert mock_update.message.reply_text.call_count >= 2
                last_call = mock_update.message.reply_text.call_args_list[-1]
                assert "couldn't find" in last_call[0][0].lower() or "context" in last_call[0][0].lower()


class TestConversationalFlow:
    """Test conversational aspects of the bot."""

    @pytest.mark.asyncio
    async def test_greeting_no_action(self, telegram_bot, mock_update, mock_context):
        """Test that greetings don't trigger actions."""
        mock_update.message.text = "Hello!"
        
        with patch.object(telegram_bot.router, 'route') as mock_route:
            from app.llm.router import RoutingDecision, ConversationIntent
            
            mock_route.return_value = RoutingDecision(
                intent=ConversationIntent.GREETING,
                confidence=1.0,
                conversational_response="Hi there! How can I help you today?",
                extracted_entities={},
                reasoning="Friendly greeting",
                requires_action=False,
                target_crew=None,
            )
            
            await telegram_bot.handle_message(mock_update, mock_context)
            
            # Verify only conversational response, no crew calls
            mock_update.message.reply_text.assert_called_once()
            assert "help" in mock_update.message.reply_text.call_args[0][0].lower()

    @pytest.mark.asyncio
    async def test_unclear_intent(self, telegram_bot, mock_update, mock_context):
        """Test handling of unclear intent."""
        mock_update.message.text = "blah blah blah"
        
        with patch.object(telegram_bot.router, 'route') as mock_route:
            from app.llm.router import RoutingDecision, ConversationIntent
            
            mock_route.return_value = RoutingDecision(
                intent=ConversationIntent.UNCLEAR,
                confidence=0.3,
                conversational_response="I'm not sure I understood that correctly. Could you rephrase?",
                extracted_entities={},
                reasoning="Cannot determine intent",
                requires_action=False,
                target_crew=None,
            )
            
            await telegram_bot.handle_message(mock_update, mock_context)
            
            # Verify clarification request
            mock_update.message.reply_text.assert_called_once()
            response = mock_update.message.reply_text.call_args[0][0].lower()
            assert "not sure" in response or "rephrase" in response or "understood" in response
