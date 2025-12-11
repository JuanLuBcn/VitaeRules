"""Basic smoke tests for Telegram media handlers."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from telegram import Update, Message, Chat, User, PhotoSize, Voice, Document, Location
from telegram.ext import ContextTypes

from app.adapters.telegram import VitaeBot
from app.config import Settings


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        telegram_bot_token="test-token-123",
        ollama_base_url="http://localhost:11434",
        ollama_model="llama2",
        database_url="sqlite:///:memory:",
    )


@pytest.fixture
def bot(settings):
    """Create VitaeBot instance."""
    return VitaeBot(settings)


@pytest.fixture
def mock_update():
    """Create mock Update object."""
    update = MagicMock(spec=Update)
    update.effective_chat = MagicMock(spec=Chat)
    update.effective_chat.id = 123456
    update.effective_user = MagicMock(spec=User)
    update.effective_user.id = 789
    update.message = MagicMock(spec=Message)
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create mock context."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot = MagicMock()
    context.bot.get_file = AsyncMock()
    return context


class TestTelegramMediaHandlers:
    """Test media handler methods exist and have basic structure."""

    def test_bot_initialization_has_media_services(self, bot):
        """Test that bot initializes with media services."""
        assert hasattr(bot, "media_handler")
        assert hasattr(bot, "whisper_service")
        assert bot.media_handler is not None
        assert bot.whisper_service is not None

    def test_handler_methods_exist(self, bot):
        """Test that all media handler methods exist."""
        assert hasattr(bot, "handle_photo")
        assert hasattr(bot, "handle_voice")
        assert hasattr(bot, "handle_document")
        assert hasattr(bot, "handle_location")
        assert callable(bot.handle_photo)
        assert callable(bot.handle_voice)
        assert callable(bot.handle_document)
        assert callable(bot.handle_location)

    @pytest.mark.anyio
    async def test_handle_photo_basic_flow(self, bot, mock_update, mock_context):
        """Test basic photo handling flow."""
        # Setup mock photo
        photo = MagicMock(spec=PhotoSize)
        photo.file_id = "test-photo-id"
        photo.width = 1920
        photo.height = 1080
        mock_update.message.photo = [photo]
        mock_update.message.caption = "Test photo"

        # Mock file download
        mock_file = MagicMock()
        mock_file.download_to_drive = AsyncMock()
        mock_context.bot.get_file.return_value = mock_file

        # Mock media handler
        with patch.object(bot.media_handler, "store_photo") as mock_store:
            mock_store.return_value = {"media_path": "photos/test.jpg"}
            
            # Mock orchestrator
            with patch.object(bot.orchestrator, "handle_message") as mock_orchestrator:
                mock_orchestrator.return_value = {"message": "Photo noted!"}

                # Call handler
                await bot.handle_photo(mock_update, mock_context)

                # Verify file was downloaded
                mock_context.bot.get_file.assert_called_once_with("test-photo-id")
                
                # Verify reply was sent
                mock_update.message.reply_text.assert_called_once()
                reply_text = mock_update.message.reply_text.call_args[0][0]
                assert "📷" in reply_text  # Photo emoji

    @pytest.mark.anyio
    async def test_handle_voice_basic_flow(self, bot, mock_update, mock_context):
        """Test basic voice handling flow."""
        # Setup mock voice
        voice = MagicMock(spec=Voice)
        voice.file_id = "test-voice-id"
        voice.duration = 5
        mock_update.message.voice = voice

        # Mock file download
        mock_file = MagicMock()
        mock_file.download_to_drive = AsyncMock()
        mock_context.bot.get_file.return_value = mock_file

        # Mock media handler and whisper
        with patch.object(bot.media_handler, "store_voice") as mock_store:
            mock_store.return_value = {"media_path": "voice/test.ogg"}
            
            with patch.object(bot.whisper_service, "is_available") as mock_available:
                mock_available.return_value = False  # No transcription for this test
                
                with patch.object(bot.orchestrator, "handle_message") as mock_orchestrator:
                    mock_orchestrator.return_value = {"message": "Voice saved!"}

                    # Call handler
                    await bot.handle_voice(mock_update, mock_context)

                    # Verify reply was sent
                    mock_update.message.reply_text.assert_called()
                    # At least one call should have voice emoji
                    calls = [call[0][0] for call in mock_update.message.reply_text.call_args_list]
                    assert any("🎤" in text for text in calls)

    @pytest.mark.anyio
    async def test_handle_document_basic_flow(self, bot, mock_update, mock_context):
        """Test basic document handling flow."""
        # Setup mock document
        document = MagicMock(spec=Document)
        document.file_id = "test-doc-id"
        document.file_name = "test.pdf"
        document.mime_type = "application/pdf"
        mock_update.message.document = document
        mock_update.message.caption = "Important document"

        # Mock file download
        mock_file = MagicMock()
        mock_file.download_to_drive = AsyncMock()
        mock_context.bot.get_file.return_value = mock_file

        # Mock media handler
        with patch.object(bot.media_handler, "store_document") as mock_store:
            mock_store.return_value = {"media_path": "documents/test.pdf"}
            
            with patch.object(bot.orchestrator, "handle_message") as mock_orchestrator:
                mock_orchestrator.return_value = {"message": "Document saved!"}

                # Call handler
                await bot.handle_document(mock_update, mock_context)

                # Verify reply was sent
                mock_update.message.reply_text.assert_called_once()
                reply_text = mock_update.message.reply_text.call_args[0][0]
                assert "📄" in reply_text  # Document emoji

    @pytest.mark.anyio
    async def test_handle_location_basic_flow(self, bot, mock_update, mock_context):
        """Test basic location handling flow."""
        # Setup mock location
        location = MagicMock(spec=Location)
        location.latitude = 40.7128
        location.longitude = -74.0060
        mock_update.message.location = location

        # Mock orchestrator
        with patch.object(bot.orchestrator, "handle_message") as mock_orchestrator:
            mock_orchestrator.return_value = {"message": "Location noted!"}

            # Call handler
            await bot.handle_location(mock_update, mock_context)

            # Verify orchestrator was called with location data
            mock_orchestrator.assert_called_once()
            call_args = mock_orchestrator.call_args[1]
            assert "40.7128" in call_args["message"]
            assert "-74.0060" in call_args["message"]

            # Verify reply was sent
            mock_update.message.reply_text.assert_called_once()
            reply_text = mock_update.message.reply_text.call_args[0][0]
            assert "📍" in reply_text  # Location emoji

    def test_create_application_registers_media_handlers(self, bot):
        """Test that media handlers are registered in application."""
        app = bot.create_application()
        
        # Get all handlers
        handlers = app.handlers.get(0, [])  # Group 0 is default
        
        # Should have handlers for commands, media, and text
        assert len(handlers) > 0
        
        # We can't easily verify the exact filters without inspecting internals,
        # but we can verify the count is correct
        # 3 commands + 4 media + 1 text = 8 total handlers
        assert len(handlers) == 8
