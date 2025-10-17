"""Telegram bot adapter for VitaeRules."""

import asyncio
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.config import Settings
from app.crews.capture.crew import CaptureCrew, CaptureContext, CaptureResult
from app.crews.retrieval.crew import RetrievalCrew, RetrievalContext, RetrievalResult
from app.memory import MemoryService
from app.tools.registry import ToolRegistry
from app.tracing import get_tracer

logger = get_tracer()


class VitaeBot:
    """Telegram bot adapter that routes messages to appropriate crews."""

    def __init__(
        self,
        settings: Settings,
        memory_service: MemoryService,
        tool_registry: ToolRegistry,
    ):
        self.settings = settings
        self.memory_service = memory_service
        self.tool_registry = tool_registry
        self.capture_crew = CaptureCrew(memory_service=memory_service)
        self.retrieval_crew = RetrievalCrew(memory_service=memory_service)

        # Storage for pending approvals and clarifications
        self.pending_approvals: dict[str, dict] = {}
        self.pending_clarifications: dict[str, dict] = {}

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user = update.effective_user
        chat_id = str(update.effective_chat.id)
        
        logger.info("start_command", extra={"chat_id": chat_id, "user": user.first_name})
        
        welcome_message = (
            f"👋 Hello {user.first_name}!\n\n"
            "I'm your personal assistant. I can help you:\n"
            "• 📝 Create tasks and lists\n"
            "• 📅 Set reminders\n"
            "• 💭 Take notes and memories\n"
            "• ❓ Answer questions about your past activities\n\n"
            "Just send me a message and I'll understand what you need!\n\n"
            "Examples:\n"
            "• \"Create task Buy groceries\"\n"
            "• \"Create list Shopping\"\n"
            "• \"Remind me to call mom tomorrow at 3pm\"\n"
            "• \"Note: had a great meeting with the team today\"\n"
            "• \"What did I do yesterday?\"\n"
            "• \"List all my tasks\""
        )
        
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        help_message = (
            "🤖 *VitaeRules Bot Help*\n\n"
            "*Capture Actions:*\n"
            "• Create tasks: \"Create task [title]\"\n"
            "• Create lists: \"Create list [name]\"\n"
            "• Add items: \"Add [item] to [list]\"\n"
            "• Set reminders: \"Remind me to [task] at [time]\"\n"
            "• Take notes: \"Note: [content]\"\n\n"
            "*Ask Questions:*\n"
            "• \"What did I do yesterday?\"\n"
            "• \"What tasks do I have?\"\n"
            "• \"When did I last meet with [person]?\"\n\n"
            "*Commands:*\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/status - Check bot status"
        )
        
        await update.message.reply_text(help_message, parse_mode="Markdown")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        chat_id = str(update.effective_chat.id)
        user_id = str(update.effective_user.id)
        
        # Get conversation history length
        history = await self.memory_service.stm.get_history(chat_id)
        
        status_message = (
            "✅ *Bot Status*\n\n"
            f"Chat ID: `{chat_id}`\n"
            f"User ID: `{user_id}`\n"
            f"Conversation messages: {len(history)}\n"
            f"Capture Crew: Active\n"
            f"Retrieval Crew: Active\n"
            f"Memory Service: Connected"
        )
        
        await update.message.reply_text(status_message, parse_mode="Markdown")

    def _is_question(self, text: str) -> bool:
        """Determine if the message is a question (route to Retrieval) or action (route to Capture)."""
        text_lower = text.lower().strip()
        
        # Question indicators
        question_words = ["what", "when", "where", "who", "why", "how", "which", "?"]
        query_verbs = ["show", "list", "find", "search", "tell me", "get"]
        
        # Check if starts with question word or ends with ?
        if any(text_lower.startswith(word) for word in question_words) or text.strip().endswith("?"):
            return True
        
        # Check for query verbs
        if any(verb in text_lower for verb in query_verbs):
            return True
        
        # Action indicators (if these are present, it's likely a capture action)
        action_words = ["create", "add", "remind", "note", "delete", "remove", "complete", "done"]
        if any(text_lower.startswith(word) for word in action_words):
            return False
        
        # Default to capture for ambiguous cases
        return False

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text messages."""
        if not update.message or not update.message.text:
            return
        
        chat_id = str(update.effective_chat.id)
        user_id = str(update.effective_user.id)
        text = update.message.text
        
        logger.info("handle_message", extra={"chat_id": chat_id, "text": text})
        
        try:
            # Route to appropriate crew
            if self._is_question(text):
                await self._handle_question(chat_id, user_id, text, update)
            else:
                await self._handle_action(chat_id, user_id, text, update)
        
        except Exception as e:
            logger.error("handle_message_error", extra={"error": str(e), "chat_id": chat_id})
            await update.message.reply_text(
                f"❌ Sorry, I encountered an error: {str(e)}\n\n"
                "Please try again or contact support if the problem persists."
            )

    async def _handle_question(
        self, chat_id: str, user_id: str, text: str, update: Update
    ) -> None:
        """Route question to RetrievalCrew."""
        await update.message.reply_text("🔍 Searching for an answer...")
        
        try:
            # Create retrieval context
            retrieval_context = RetrievalContext(
                chat_id=chat_id,
                user_id=user_id,
                memory_service=self.memory_service,
            )
            
            # Call RetrievalCrew (sync method)
            result: RetrievalResult = self.retrieval_crew.retrieve(
                user_question=text,
                context=retrieval_context,
            )
            
            # Format response
            response = f"💡 *Answer:*\n{result.answer.answer}\n"
            
            if result.answer.citations:
                response += f"\n📚 *Sources:*\n"
                for idx, citation in enumerate(result.answer.citations[:5], 1):  # Limit to 5 sources
                    response += f"{idx}. {citation.title}\n"
            
            if result.answer.confidence < 0.5:
                response += "\n⚠️ _Note: Low confidence answer. Information may be limited._"
            
            await update.message.reply_text(response, parse_mode="Markdown")
        
        except Exception as e:
            logger.error("retrieval_error", extra={"error": str(e), "chat_id": chat_id})
            await update.message.reply_text(
                "❌ I couldn't find a good answer. Try rephrasing your question or check if I have enough information."
            )

    async def _handle_action(
        self, chat_id: str, user_id: str, text: str, update: Update
    ) -> None:
        """Route action to CaptureCrew."""
        await update.message.reply_text("⚙️ Processing your request...")
        
        try:
            # Create capture context with callbacks
            capture_context = CaptureContext(
                chat_id=chat_id,
                user_id=user_id,
                auto_approve=False,  # Require user approval
                approval_callback=lambda tool, params: self._request_approval(
                    chat_id, tool, params, update
                ),
                clarification_callback=lambda questions: self._request_clarification(
                    chat_id, questions, update
                ),
            )
            
            # Call CaptureCrew
            result: CaptureResult = await self.capture_crew.capture(
                user_input=text,
                context=capture_context,
            )
            
            # Format response
            if result.summary:
                response = f"✅ {result.summary}"
            else:
                response = "✅ Done!"
            
            if result.clarifications_asked:
                response += f"\n\n💬 Asked {len(result.clarifications_asked)} clarification(s)"
            
            if result.actions_executed:
                response += f"\n🔧 Executed {result.actions_executed} action(s)"
            
            await update.message.reply_text(response)
        
        except Exception as e:
            logger.error("capture_error", extra={"error": str(e), "chat_id": chat_id})
            await update.message.reply_text(
                f"❌ I couldn't complete that action: {str(e)}"
            )

    async def _request_approval(
        self, chat_id: str, tool: str, params: dict, update: Update
    ) -> bool:
        """Request approval from user via inline keyboard."""
        approval_id = f"{chat_id}_{len(self.pending_approvals)}"
        
        # Format approval message
        message = (
            f"⚠️ *Approval Required*\n\n"
            f"Tool: `{tool}`\n"
            f"Action: {params.get('operation', 'unknown')}\n\n"
            f"Do you want to proceed?"
        )
        
        # Create inline keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{approval_id}"),
                InlineKeyboardButton("❌ Deny", callback_data=f"deny_{approval_id}"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Store approval request
        approval_event = asyncio.Event()
        self.pending_approvals[approval_id] = {
            "tool": tool,
            "params": params,
            "event": approval_event,
            "approved": False,
        }
        
        # Send approval request
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
        
        # Wait for user response (with timeout)
        try:
            await asyncio.wait_for(approval_event.wait(), timeout=self.settings.approval_timeout_minutes * 60)
            return self.pending_approvals[approval_id]["approved"]
        except asyncio.TimeoutError:
            logger.warning("approval_timeout", extra={"chat_id": chat_id, "approval_id": approval_id})
            await update.message.reply_text("⏱️ Approval request timed out.")
            return False
        finally:
            # Cleanup
            self.pending_approvals.pop(approval_id, None)

    async def _request_clarification(
        self, chat_id: str, questions: dict[str, str], update: Update
    ) -> dict[str, str]:
        """Request clarifications from user."""
        clarification_id = f"{chat_id}_{len(self.pending_clarifications)}"
        
        # Format clarification message
        message = "❓ *I need some more information:*\n\n"
        for field, question in questions.items():
            message += f"• {question}\n"
        
        message += "\nPlease provide the answers (one per line)."
        
        # Store clarification request
        clarification_event = asyncio.Event()
        self.pending_clarifications[clarification_id] = {
            "questions": questions,
            "event": clarification_event,
            "answers": {},
        }
        
        await update.message.reply_text(message, parse_mode="Markdown")
        
        # Wait for user response (with timeout)
        try:
            await asyncio.wait_for(
                clarification_event.wait(),
                timeout=self.settings.approval_timeout_minutes * 60
            )
            return self.pending_clarifications[clarification_id]["answers"]
        except asyncio.TimeoutError:
            logger.warning("clarification_timeout", extra={"chat_id": chat_id})
            await update.message.reply_text("⏱️ Clarification request timed out.")
            return {}
        finally:
            # Cleanup
            self.pending_clarifications.pop(clarification_id, None)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle inline keyboard button presses."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data.startswith("approve_"):
            approval_id = data.replace("approve_", "")
            if approval_id in self.pending_approvals:
                self.pending_approvals[approval_id]["approved"] = True
                self.pending_approvals[approval_id]["event"].set()
                await query.edit_message_text("✅ Approved!")
        
        elif data.startswith("deny_"):
            approval_id = data.replace("deny_", "")
            if approval_id in self.pending_approvals:
                self.pending_approvals[approval_id]["approved"] = False
                self.pending_approvals[approval_id]["event"].set()
                await query.edit_message_text("❌ Denied.")

    def create_application(self) -> Application:
        """Create and configure the Telegram application."""
        # Create application
        application = (
            Application.builder()
            .token(self.settings.telegram_bot_token)
            .build()
        )
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        application.add_handler(CallbackQueryHandler(self.handle_callback))
        
        logger.info("telegram_application_created", extra={"bot": "VitaeBot"})
        
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
        
        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("telegram_bot_stopping")
        finally:
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
