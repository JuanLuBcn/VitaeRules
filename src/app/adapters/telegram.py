"""Telegram bot adapter for VitaeRules - CHATCREW ARCHITECTURE."""

import asyncio
import tempfile
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.config import Settings
from app.crews.capture import CaptureCrew
from app.crews.chat import ChatContext, ChatCrew
from app.crews.search import SearchContext, UnifiedSearchCrew
from app.llm import LLMService
from app.memory import MemoryService
from app.services import MediaHandler, WhisperService
from app.tools.registry import ToolRegistry
from app.tracing import get_tracer

logger = get_tracer()


class VitaeBot:
    """Conversational Telegram bot with ChatCrew architecture."""

    def __init__(
        self,
        settings: Settings,
        memory_service: MemoryService,
        tool_registry: ToolRegistry,
        llm_service: LLMService,
    ):
        self.settings = settings
        self.memory_service = memory_service
        self.tool_registry = tool_registry
        self.llm_service = llm_service
        
        # Initialize specialized crews
        logger.info("Initializing CrewAI crews for Telegram bot...")
        
        # UnifiedSearchCrew - handles multi-source search
        self.search_crew = UnifiedSearchCrew(
            memory_service=memory_service,
            task_tool=tool_registry.get("task_tool"),
            list_tool=tool_registry.get("list_tool"),
            llm=llm_service,
        )
        logger.info("UnifiedSearchCrew initialized")
        
        # CaptureCrew - handles action execution
        self.capture_crew = CaptureCrew(
            memory_service=memory_service,
            llm=llm_service,
        )
        logger.info("CaptureCrew initialized")
        
        # ChatCrew - main conversational interface with delegation
        self.chat_crew = ChatCrew(
            memory_service=memory_service,
            search_crew=self.search_crew,
            capture_crew=self.capture_crew,
            llm=llm_service,
        )
        logger.info("ChatCrew initialized")
        
        # Media services
        self.media_handler = MediaHandler()
        self.whisper_service = WhisperService(model_name="base")
        
        logger.info("VitaeBot initialized with ChatCrew architecture")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user = update.effective_user
        chat_id = str(update.effective_chat.id)
        
        logger.info("start_command", extra={"chat_id": chat_id, "user": user.first_name})
        
        welcome_message = (
            f"👋 Hello {user.first_name}!\n\n"
            "I'm your personal assistant powered by ChatCrew with CrewAI! "
            "I can have natural conversations, search your information, and execute actions.\n\n"
            "**What I can do:**\n"
            "• � **Chat** - Natural conversation, answer questions\n"
            "• 🔍 **Search** - Find information in your memories, tasks, and lists\n"
            "• ⚡ **Actions** - Create tasks, add to lists, save notes\n\n"
            "**Examples:**\n"
            "• \"Hello! How are you?\"\n"
            "• \"What did I discuss with Sarah?\"\n"
            "• \"Remind me to call John tomorrow at 3pm\"\n"
            "• \"Add milk to shopping list\"\n\n"
            "Just chat naturally - I'll understand! 😊"
        )
        
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        help_message = (
            "🤖 **VitaeRules Bot - ChatCrew Architecture**\n\n"
            "I use CrewAI with three specialized crews:\n\n"
            "**� Chat (Conversational)**\n"
            "• Greetings: \"Hello!\", \"How are you?\"\n"
            "• Casual questions: \"Tell me a joke\"\n"
            "• Small talk and conversation\n\n"
            "**🔍 Search (Information Retrieval)**\n"
            "• Memory search: \"What did I discuss with Sarah?\"\n"
            "• Task queries: \"What tasks do I have for today?\"\n"
            "• List queries: \"What's on my shopping list?\"\n"
            "• Multi-source search across all your data\n\n"
            "**⚡ Actions (Execution)**\n"
            "• Create tasks: \"Remind me to call John tomorrow\"\n"
            "• Add to lists: \"Add milk to shopping list\"\n"
            "• Save notes: \"Remember that Sarah likes coffee\"\n"
            "• Execute commands and modifications\n\n"
            "**🔄 Context Awareness:**\n"
            "I remember our conversation! You can:\n"
            "• Ask follow-up questions\n"
            "• Refer to previous messages\n"
            "• Update or modify recent actions\n\n"
            "**📸 Media Support:**\n"
            "• Photos, voice notes, documents, locations\n\n"
            "**Commands:**\n"
            "/start - Start the bot\n"
            "/help - Show this help\n"
            "/status - Check status"
        )
        
        await update.message.reply_text(help_message)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        chat_id = str(update.effective_chat.id)
        user_id = str(update.effective_user.id)
        
        # Get conversation history length
        history = self.memory_service.stm.get_history(chat_id)
        
        status_message = (
            "✅ **Bot Status**\n\n"
            f"Chat ID: `{chat_id}`\n"
            f"User ID: `{user_id}`\n"
            f"Messages in session: {len(history)}\n\n"
            "**Architecture:** ChatCrew with CrewAI\n"
            "**Crews:**\n"
            "  • ChatCrew - Conversational interface\n"
            "  • UnifiedSearchCrew - Multi-source search\n"
            "  • CaptureCrew - Action execution\n"
            "**Memory:** Connected (STM + LTM + Entity)\n"
            "**LLM:** Active (Ollama)"
        )
        
        await update.message.reply_text(status_message, parse_mode="Markdown")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle incoming text messages with ChatCrew architecture.
        
        Flow:
        1. Message → ChatCrew
        2. IntentAnalyzer classifies intent (CHAT/SEARCH/ACTION)
        3. ChatCrew delegates to:
           - Direct response (CHAT)
           - UnifiedSearchCrew (SEARCH)
           - CaptureCrew (ACTION)
        4. ResponseComposer creates natural response
        5. Returns result to user
        
        ChatCrew handles:
        - Intent classification
        - Conversation context
        - Delegation to specialized crews
        - Natural language responses
        """
        if not update.message or not update.message.text:
            return
        
        chat_id = str(update.effective_chat.id)
        user_id = str(update.effective_user.id)
        text = update.message.text
        
        logger.info(
            "message_received",
            extra={
                "chat_id": chat_id,
                "user": update.effective_user.first_name,
                "message_length": len(text),
            }
        )
        
        try:
            # Get conversation history for context
            history = self.memory_service.stm.get_history(chat_id, limit=5)
            conversation_history = [
                {"role": msg.role, "content": msg.content}
                for msg in history
            ]
            
            # Create chat context
            chat_context = ChatContext(
                chat_id=chat_id,
                user_id=user_id,
                conversation_history=conversation_history,
            )
            
            # ChatCrew handles everything with CrewAI orchestration
            response = await self.chat_crew.chat_with_crew_tasks(
                user_message=text,
                context=chat_context,
            )
            
            # Send response to user
            await update.message.reply_text(response.message)
            
            logger.info(
                "message_processed",
                extra={
                    "chat_id": chat_id,
                    "intent": response.intent.value,
                    "searched": response.searched,
                    "acted": response.acted,
                }
            )
        
        except Exception as e:
            logger.exception(
                "message_error",
                extra={"error": str(e), "chat_id": chat_id, "message": text[:100]}
            )
            await update.message.reply_text(
                "I'm sorry, I encountered an error processing your message. "
                "Could you try rephrasing that?\n\n"
                f"Error: {str(e)}"
            )

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle photo messages."""
        if not update.message or not update.message.photo:
            return
        
        chat_id = str(update.effective_chat.id)
        user_id = str(update.effective_user.id)
        caption = update.message.caption or ""
        
        logger.info("photo_received", extra={"chat_id": chat_id, "has_caption": bool(caption)})
        
        try:
            # Get the largest photo
            photo = update.message.photo[-1]
            
            # Download to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                file = await context.bot.get_file(photo.file_id)
                await file.download_to_drive(tmp_file.name)
                tmp_path = Path(tmp_file.name)
            
            # Store photo
            metadata = {
                "caption": caption,
                "telegram_file_id": photo.file_id,
                "width": photo.width,
                "height": photo.height,
            }
            
            result = await self.media_handler.store_photo(tmp_path, user_id, metadata)
            
            # Clean up temp file
            tmp_path.unlink()
            
            # Process caption with orchestrator if present
            message_text = f"Photo stored: {result['media_path']}"
            if caption:
                # Pass photo context to orchestrator with media path embedded
                # The orchestrator will extract media_type and clean message,
                # then we'll update the media_reference with the actual path
                orchestrator_message = f"[Photo attached] {caption}"
                
                # We need to manually add media_path to the message for the orchestrator
                # Actually, let's use a better approach: pass it in the formatted message
                orchestrator_message = f"[Photo: {result['media_path']}] {caption}"
                
                orchestrator_result = await self.orchestrator.handle_message(
                    message=orchestrator_message,
                    chat_id=chat_id,
                    user_id=user_id,
                )
                message_text = f"📷 Photo saved!\n\n{orchestrator_result['message']}"
            else:
                message_text = "📷 Photo saved! Add a caption to include it in your memories."
            
            await update.message.reply_text(message_text)
            
            logger.info(
                "photo_processed",
                extra={"chat_id": chat_id, "media_path": result["media_path"]}
            )
        
        except Exception as e:
            logger.exception("photo_error", extra={"error": str(e), "chat_id": chat_id})
            await update.message.reply_text(
                f"Sorry, I couldn't process your photo: {str(e)}"
            )

    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle voice messages with Whisper transcription."""
        if not update.message or not update.message.voice:
            return
        
        chat_id = str(update.effective_chat.id)
        user_id = str(update.effective_user.id)
        
        logger.info("voice_received", extra={"chat_id": chat_id})
        
        try:
            voice = update.message.voice
            
            # Download to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_file:
                file = await context.bot.get_file(voice.file_id)
                await file.download_to_drive(tmp_file.name)
                tmp_path = Path(tmp_file.name)
            
            # Transcribe with Whisper
            transcription_text = ""
            if self.whisper_service.is_available():
                await update.message.reply_text("🎤 Transcribing your voice message...")
                transcription = await self.whisper_service.transcribe(tmp_path, language=None)
                if transcription.get("success"):
                    transcription_text = transcription["text"]
                    logger.info(
                        "voice_transcribed",
                        extra={
                            "chat_id": chat_id,
                            "language": transcription.get("language"),
                            "length": len(transcription_text)
                        }
                    )
            
            # Store voice note
            metadata = {
                "telegram_file_id": voice.file_id,
                "duration": voice.duration,
                "transcription": transcription_text,
            }
            
            result = await self.media_handler.store_voice(tmp_path, user_id, metadata)
            
            # Clean up temp file
            tmp_path.unlink()
            
            # Process transcription with orchestrator
            if transcription_text:
                orchestrator_message = f"[Voice: {result['media_path']}] {transcription_text}"
                orchestrator_result = await self.orchestrator.handle_message(
                    message=orchestrator_message,
                    chat_id=chat_id,
                    user_id=user_id,
                )
                message_text = f"🎤 Voice transcribed:\n\"{transcription_text}\"\n\n{orchestrator_result['message']}"
            else:
                message_text = "🎤 Voice note saved (transcription unavailable)."
            
            await update.message.reply_text(message_text)
            
            logger.info(
                "voice_processed",
                extra={"chat_id": chat_id, "media_path": result["media_path"]}
            )
        
        except Exception as e:
            logger.exception("voice_error", extra={"error": str(e), "chat_id": chat_id})
            await update.message.reply_text(
                f"Sorry, I couldn't process your voice message: {str(e)}"
            )

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle document messages."""
        if not update.message or not update.message.document:
            return
        
        chat_id = str(update.effective_chat.id)
        user_id = str(update.effective_user.id)
        caption = update.message.caption or ""
        
        logger.info("document_received", extra={"chat_id": chat_id, "has_caption": bool(caption)})
        
        try:
            document = update.message.document
            file_name = document.file_name or "document"
            
            # Download to temporary file
            suffix = Path(file_name).suffix or ".bin"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                file = await context.bot.get_file(document.file_id)
                await file.download_to_drive(tmp_file.name)
                tmp_path = Path(tmp_file.name)
            
            # Store document
            metadata = {
                "caption": caption,
                "telegram_file_id": document.file_id,
                "original_name": file_name,
                "mime_type": document.mime_type,
            }
            
            result = await self.media_handler.store_document(tmp_path, user_id, metadata)
            
            # Clean up temp file
            tmp_path.unlink()
            
            # Process caption if present
            message_text = f"📄 Document \"{file_name}\" saved!"
            if caption:
                orchestrator_message = f"[Document: {file_name} | {result['media_path']}] {caption}"
                orchestrator_result = await self.orchestrator.handle_message(
                    message=orchestrator_message,
                    chat_id=chat_id,
                    user_id=user_id,
                )
                message_text = f"📄 Document saved!\n\n{orchestrator_result['message']}"
            
            await update.message.reply_text(message_text)
            
            logger.info(
                "document_processed",
                extra={"chat_id": chat_id, "media_path": result["media_path"]}
            )
        
        except Exception as e:
            logger.exception("document_error", extra={"error": str(e), "chat_id": chat_id})
            await update.message.reply_text(
                f"Sorry, I couldn't process your document: {str(e)}"
            )

    async def handle_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle location messages."""
        if not update.message or not update.message.location:
            return
        
        chat_id = str(update.effective_chat.id)
        user_id = str(update.effective_user.id)
        
        logger.info("location_received", extra={"chat_id": chat_id})
        
        try:
            location = update.message.location
            
            # Format location message
            location_text = (
                f"Location shared: {location.latitude}, {location.longitude}"
            )
            
            # Pass to orchestrator (it can extract location for enrichment)
            orchestrator_result = await self.orchestrator.handle_message(
                message=f"[Location: lat={location.latitude}, lon={location.longitude}] "
                        f"I'm sharing my location",
                chat_id=chat_id,
                user_id=user_id,
            )
            
            message_text = f"📍 {orchestrator_result['message']}"
            
            await update.message.reply_text(message_text)
            
            logger.info(
                "location_processed",
                extra={
                    "chat_id": chat_id,
                    "latitude": location.latitude,
                    "longitude": location.longitude
                }
            )
        
        except Exception as e:
            logger.exception("location_error", extra={"error": str(e), "chat_id": chat_id})
            await update.message.reply_text(
                f"Sorry, I couldn't process your location: {str(e)}"
            )

    def create_application(self) -> Application:
        """Create and configure the Telegram application."""
        application = (
            Application.builder()
            .token(self.settings.telegram_bot_token)
            .build()
        )
        
        # Add command handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("status", self.status_command))
        
        # Add media handlers
        application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        application.add_handler(MessageHandler(filters.VOICE, self.handle_voice))
        application.add_handler(MessageHandler(filters.Document.ALL, self.handle_document))
        application.add_handler(MessageHandler(filters.LOCATION, self.handle_location))
        
        # Add message handler (handles ALL text messages)
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        logger.info(
            "telegram_app_created",
            extra={
                "architecture": "agent-based",
                "agents": ["List", "Task", "Note", "Query"],
                "media_support": ["photo", "voice", "document", "location"]
            }
        )
        
        return application

    async def run(self) -> None:
        """Run the Telegram bot."""
        application = self.create_application()
        
        logger.info("telegram_bot_starting")
        
        # Start the bot
        await application.initialize()
        await application.start()
        await application.updater.start_polling()
        
        logger.info("telegram_bot_running")
        
        # Keep running until interrupted
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("telegram_bot_stopping")
        finally:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
            logger.info("telegram_bot_stopped")
