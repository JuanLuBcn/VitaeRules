"""Telegram bot adapter for VitaeRules - NEW AGENT ARCHITECTURE."""

import asyncio

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.agents.orchestrator import AgentOrchestrator
from app.config import Settings
from app.llm import LLMService
from app.memory import MemoryService
from app.tools.registry import ToolRegistry
from app.tracing import get_tracer

logger = get_tracer()


class VitaeBot:
    """Conversational Telegram bot with agent-based architecture."""

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
        
        # NEW: Simple agent-based orchestrator - handles ALL message routing
        self.orchestrator = AgentOrchestrator(llm_service, memory_service)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user = update.effective_user
        chat_id = str(update.effective_chat.id)
        
        logger.info("start_command", extra={"chat_id": chat_id, "user": user.first_name})
        
        welcome_message = (
            f"👋 Hello {user.first_name}!\n\n"
            "I'm your personal assistant powered by specialized AI agents. I can help you:\n\n"
            "• 📋 **Manage Lists** - Add items, query contents\n"
            "• ✅ **Track Tasks** - Create reminders, deadlines\n"
            "• 💾 **Save Notes** - Remember important information\n"
            "• ❓ **Answer Questions** - Search your memories\n\n"
            "Just send me a message in natural language!\n\n"
            "**Examples:**\n"
            "• \"Add milk to shopping list\"\n"
            "• \"Remind me to call John tomorrow\"\n"
            "• \"Remember that Sarah likes coffee\"\n"
            "• \"What did I do yesterday?\""
        )
        
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        help_message = (
            "🤖 **VitaeRules Bot - Help**\n\n"
            "**📋 Lists:**\n"
            "• \"Add [item] to [list]\"\n"
            "• \"What's on my shopping list?\"\n"
            "• \"Add milk, eggs and bread\"\n\n"
            "**✅ Tasks:**\n"
            "• \"Remind me to [task]\"\n"
            "• \"Create task: finish report by Friday\"\n"
            "• \"What are my tasks?\"\n\n"
            "**💾 Notes:**\n"
            "• \"Remember that [fact]\"\n"
            "• \"Note: John's birthday is May 15\"\n"
            "• \"Save this: meeting went well\"\n\n"
            "**❓ Questions:**\n"
            "• \"What did I do yesterday?\"\n"
            "• \"Tell me about [topic]\"\n"
            "• \"When did I last meet John?\"\n\n"
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
        history = await self.memory_service.stm.get_history(chat_id)
        
        status_message = (
            "✅ **Bot Status**\n\n"
            f"Chat ID: `{chat_id}`\n"
            f"User ID: `{user_id}`\n"
            f"Messages in session: {len(history)}\n\n"
            "**Architecture:** Agent-based\n"
            "**Agents:** List, Task, Note, Query\n"
            "**Memory:** Connected\n"
            "**LLM:** Active"
        )
        
        await update.message.reply_text(status_message, parse_mode="Markdown")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle incoming text messages with NEW agent-based architecture.
        
        Flow:
        1. Message → AgentOrchestrator
        2. Orchestrator classifies intent
        3. Routes to appropriate agent (List/Task/Note/Query)
        4. Agent handles everything (extraction, confirmation, execution)
        5. Returns result to user
        
        NO old heuristics (is_question, is_list_query, etc.)
        NO Router/Planner/Enricher/Clarifier complexity
        SIMPLE and CLEAN!
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
            # NEW ARCHITECTURE: Orchestrator handles EVERYTHING
            result = await self.orchestrator.handle_message(
                message=text,
                chat_id=chat_id,
                user_id=user_id,
            )
            
            # Send response to user
            await update.message.reply_text(result["message"])
            
            logger.info(
                "message_processed",
                extra={
                    "chat_id": chat_id,
                    "success": result.get("success", True),
                    "needs_confirmation": result.get("needs_confirmation", False),
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
        
        # Add message handler (handles ALL text messages)
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        
        logger.info(
            "telegram_app_created",
            extra={"architecture": "agent-based", "agents": ["List", "Task", "Note", "Query"]}
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
