"""Telegram bot adapter for VitaeRules - NEW AGENT ARCHITECTURE."""

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
        
        # NEW: Simple agent-based orchestrator
        self.orchestrator = AgentOrchestrator(llm_service, memory_service)

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
            f"Conversational Router: LLM-powered\n"
            f"Memory Service: Connected"
        )
        
        await update.message.reply_text(status_message, parse_mode="Markdown")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text messages with NEW agent-based architecture."""
        if not update.message or not update.message.text:
            return
        
        chat_id = str(update.effective_chat.id)
        user_id = str(update.effective_user.id)
        text = update.message.text
        
        logger.info(f"Message received", extra={"chat_id": chat_id, "user": update.effective_user.first_name})
        
        try:
            # NEW ARCHITECTURE: Simple orchestrator handles everything
            result = await self.orchestrator.handle_message(
                message=text,
                chat_id=chat_id,
                user_id=user_id,
            )
            
            # Send response to user
            await update.message.reply_text(result["message"])
            
            logger.info("Message processed successfully", extra={"chat_id": chat_id})
        
        except Exception as e:
            logger.exception("handle_message_error", extra={"error": str(e), "chat_id": chat_id})
            await update.message.reply_text(
                f"I'm sorry, I encountered an error. Could you try rephrasing that?\n\n"
                f"Error: {str(e)}"
            )

    def create_application(self) -> Application:
        self, update: Update, session, text: str, chat_id: str, user_id: str
    ) -> None:
        """Handle the initial message in a conversation (PHASE 1)."""
        # Get conversation history for context
        history = self.memory_service.stm.get_history(chat_id)
        conv_history = [
            {"role": msg.role, "content": msg.content}
            for msg in history[-5:]  # Last 5 messages
        ]
        
        # PHASE 1: Intent Detection
        print(f"\n🧠 PHASE 1: Intent Detection")
        print(f"{'─'*80}")
        
        # Quick list query check - handle list queries directly
        from .question_detection import is_list_query, extract_list_name
        if is_list_query(text):
            print(f"✓ Quick detection: LIST QUERY")
            print(f"✓ Skipping enrichment flow → Direct to list tool")
            
            await self._handle_list_query(update, text, chat_id, user_id)
            session.reset()  # Clear session
            return
        
        # Quick question check - bypass enrichment for obvious questions
        if is_question(text):
            print(f"✓ Quick detection: QUESTION (has ? or question words)")
            print(f"✓ Skipping enrichment flow → Direct to retrieval")
            
            # Route directly to retrieval
            await update.message.reply_text("Let me search my memory for that...")
            await self._execute_retrieval(chat_id, user_id, text, update)
            session.reset()  # Clear session
            return
        
        # Use LLM for intent detection
        routing_context = ConversationContext(
            user_message=text,
            chat_id=chat_id,
            user_id=user_id,
            conversation_history=conv_history,
        )
        
        decision = self.router.route(routing_context)
        
        print(f"✓ Intent: {decision.intent.value}")
        print(f"✓ Confidence: {decision.confidence:.2%}")
        if decision.extracted_entities:
            print(f"✓ Entities: {decision.extracted_entities}")
        
        # Store in session
        session.original_message = text
        session.intent = decision.intent.value
        session.target_crew = decision.target_crew
        session.collected_data = decision.extracted_entities or {}
        
        # PHASE 2: Conversational Response
        print(f"\n💭 PHASE 2: Conversational Response")
        print(f"{'─'*80}")
        print(f"✓ Response: {decision.conversational_response}")
        
        await update.message.reply_text(decision.conversational_response)
        
        # PHASE 3: Determine next step based on intent
        if decision.intent in [ConversationIntent.GREETING, ConversationIntent.HELP, ConversationIntent.UNCLEAR]:
            # No action needed - just conversational
            print(f"✓ No action required (conversational only)")
            session.reset()
            return
        
        if decision.target_crew == "retrieval":
            # Questions go straight to retrieval (no confirmation needed)
            print(f"\n⚡ PHASE 3: Direct Retrieval")
            print(f"{'─'*80}")
            await self._execute_retrieval(chat_id, user_id, text, update)
            session.reset()
            return
        
        # ============ PHASE 3: Ambiguity Detection ============
        print(f"\n🔍 PHASE 3A: Checking for ambiguity...")
        clarification = self.clarification_detector.detect_ambiguity(
            text,
            current_intent=session.intent,
            collected_data=session.collected_data
        )
        
        if clarification:
            print(f"✓ Ambiguity detected: {clarification['type']}")
            print(f"✓ Confidence: {clarification['confidence']:.2%}")
            
            # Store clarification options and move to clarifying state
            session.state = ConversationState.CLARIFYING
            session.clarification_options = clarification.get('options', [])
            session.last_question = clarification['question']
            session.update_activity()
            
            # Present options to user
            if session.clarification_options:
                options_text = "\n".join([
                    f"{i+1}. {opt['label']}: {opt['interpretation']}"
                    for i, opt in enumerate(session.clarification_options)
                ])
                
                question = f"{clarification['question']}\n\n{options_text}\n\nPlease choose a number or explain in your own words."
            else:
                question = clarification['question']
            
            await update.message.reply_text(question)
            return
        
        print(f"✓ No ambiguity detected - proceeding")
        
        # For capture actions, check if we need enrichment
        print(f"\n🔄 PHASE 3B: Checking if enrichment needed...")
        if self.enricher.needs_enrichment(session.intent, session.collected_data):
            print(f"✓ Enrichment beneficial - asking follow-up questions")
            # Generate first follow-up question
            follow_up = self.enricher.generate_follow_up_questions(
                session.intent,
                session.original_message,
                session.collected_data,
                session.follow_up_count
            )
            
            if follow_up:
                session.state = ConversationState.GATHERING_DETAILS
                session.record_follow_up()
                session.last_question = follow_up  # Store for corrections
                print(f"✓ Follow-up question: {follow_up[:50]}...")
                await update.message.reply_text(follow_up)
                return
        
        print(f"✓ No enrichment needed - moving to confirmation")
        # Move directly to confirmation flow
        await self._show_confirmation_preview(update, session, chat_id, user_id)
    
    async def _handle_follow_up_response(
        self, update: Update, session, text: str, chat_id: str, user_id: str
    ) -> None:
        """Handle response to a follow-up question (PHASE 2 - Enrichment)."""
        print(f"\n📝 PHASE 2: Processing Follow-up Response")
        print(f"{'─'*80}")
        
        # Extract information from the follow-up response
        session.collected_data = self.enricher.extract_info_from_response(
            session.intent, text, session.collected_data
        )
        
        print(f"✓ Extracted info from: {text[:50]}...")
        print(f"✓ Updated data: people={session.collected_data.get('people', [])}, "
              f"places={session.collected_data.get('places', [])}")
        
        # Check if we should ask more questions
        if session.can_ask_more_questions() and self.enricher.needs_enrichment(session.intent, session.collected_data):
            # Generate another follow-up
            follow_up = self.enricher.generate_follow_up_questions(
                session.intent,
                session.original_message,
                session.collected_data,
                session.follow_up_count
            )
            
            if follow_up:
                session.record_follow_up()
                session.last_question = follow_up  # Store for corrections
                print(f"✓ Asking another follow-up question...")
                await update.message.reply_text(follow_up)
                return
        
        # No more questions needed - move to confirmation
        print(f"✓ Enrichment complete - moving to confirmation")
        await self._show_confirmation_preview(update, session, chat_id, user_id)
    
    async def _handle_confirmation_response(
        self, update: Update, session, text: str, chat_id: str, user_id: str
    ) -> None:
        """Handle yes/no response to confirmation (PHASE 3 - Execution)."""
        print(f"\n✅ PHASE 3: Processing Confirmation")
        print(f"{'─'*80}")
        
        if is_affirmative(text):
            print(f"✓ User confirmed: YES")
            
            # Special handling for list_manage with multiple items
            if session.intent == "list_manage" and "parsed_items" in session.collected_data:
                await self._execute_list_add(session, chat_id, user_id, update)
            else:
                # Execute the pending action normally
                await self._execute_capture(session, chat_id, user_id, update)
            
            session.reset()
        
        elif is_negative(text):
            print(f"✓ User cancelled: NO")
            await update.message.reply_text("Okay, I won't save that. Let me know if you need anything else!")
            session.reset()
        
        else:
            # Unclear response
            print(f"⚠️  Unclear confirmation response: {text}")
            await update.message.reply_text(
                "I didn't quite understand. Please reply:\n"
                "• 'yes' or 'si' to confirm\n"
                "• 'no' to cancel"
            )
    
    async def _handle_clarification_response(
        self, update: Update, session, text: str, chat_id: str, user_id: str
    ) -> None:
        """Handle user's response to clarification question (PHASE 3)."""
        print(f"\n🔍 PHASE 3: Processing Clarification Response")
        print(f"{'─'*80}")
        
        # Check if user selected a numbered option
        if session.clarification_options and text.strip().isdigit():
            option_idx = int(text.strip()) - 1
            
            if 0 <= option_idx < len(session.clarification_options):
                selected = session.clarification_options[option_idx]
                print(f"✓ User selected option {option_idx + 1}: {selected['label']}")
                
                # Update intent and data based on selected interpretation
                session.intent = selected.get('intent', session.intent)
                session.collected_data['title'] = selected.get('interpretation', session.collected_data.get('title', ''))
                
                await update.message.reply_text(f"Got it! {selected['interpretation']}")
            else:
                print(f"⚠️  Invalid option number: {text}")
                await update.message.reply_text(
                    f"Please choose a number between 1 and {len(session.clarification_options)}, or explain in your own words."
                )
                return
        else:
            # User provided free-form clarification
            print(f"✓ User provided free-form clarification")
            
            # Append clarification to content
            current_content = session.collected_data.get('content', session.original_message)
            session.collected_data['content'] = f"{current_content}\n\nClarification: {text}".strip()
        
        # Move to enrichment or confirmation
        session.state = ConversationState.INITIAL  # Reset to re-evaluate
        session.clarification_options = []
        
        # Continue with normal flow (enrichment check)
        if self.enricher.needs_enrichment(session.intent, session.collected_data):
            print(f"✓ Still needs enrichment after clarification")
            follow_up = self.enricher.generate_follow_up_questions(
                session.intent,
                session.collected_data.get('content', ''),
                session.collected_data,
                session.follow_up_count
            )
            
            if follow_up:
                session.state = ConversationState.GATHERING_DETAILS
                session.record_follow_up()
                session.last_question = follow_up
                await update.message.reply_text(follow_up)
                return
        
        # Go straight to confirmation
        print(f"✓ Clarification complete - moving to confirmation")
        await self._show_confirmation_preview(update, session, chat_id, user_id)
    
    async def _handle_correction(
        self, update: Update, session, text: str, chat_id: str, user_id: str
    ) -> None:
        """Handle user correction to previously provided information (PHASE 3)."""
        print(f"\n🔄 PHASE 3: Processing Correction")
        print(f"{'─'*80}")
        print(f"✓ Correction text: {text}")
        
        # Apply correction using LLM
        updated_data = self.correction_handler.apply_correction(
            correction_text=text,
            last_question=session.last_question,
            collected_data=session.collected_data
        )
        
        session.collected_data = updated_data
        print(f"✓ Data updated after correction")
        
        await update.message.reply_text("Got it, I've updated that information.")
        
        # Continue with flow - check if more enrichment needed
        if session.state == ConversationState.GATHERING_DETAILS:
            # Check if we should ask more questions
            if session.can_ask_more_questions() and self.enricher.needs_enrichment(session.intent, session.collected_data):
                follow_up = self.enricher.generate_follow_up_questions(
                    session.intent,
                    session.original_message,
                    session.collected_data,
                    session.follow_up_count
                )
                
                if follow_up:
                    session.record_follow_up()
                    session.last_question = follow_up
                    await update.message.reply_text(follow_up)
                    return
            
            # No more questions - move to confirmation
            await self._show_confirmation_preview(update, session, chat_id, user_id)
        
        elif session.state == ConversationState.CLARIFYING:
            # Re-ask clarification question or move forward
            await self._show_confirmation_preview(update, session, chat_id, user_id)
    
    async def _show_confirmation_preview(
        self, update: Update, session, chat_id: str, user_id: str
    ) -> None:
        """Show preview and ask for confirmation."""
        print(f"\n🔍 Generating Preview")
        print(f"{'─'*80}")
        
        # Generate preview based on intent
        if session.intent == "note_taking":
            title = session.collected_data.get("title", session.original_message[:50])
            content = session.collected_data.get("content", session.original_message)
            tags = session.collected_data.get("tags", [])
            people = session.collected_data.get("people", [])
            places = session.collected_data.get("places", [])
            
            preview = (
                f"📝 *I'll save this as a memory:*\n\n"
                f"*Title:* {title}\n"
                f"*Content:* {content[:100]}...\n" if len(content) > 100 else f"*Content:* {content}\n"
            )
            
            if people:
                preview += f"*People:* {', '.join(people)}\n"
            
            if places:
                preview += f"*Places:* {', '.join(places)}\n"
            
            if tags:
                preview += f"*Tags:* {', '.join(tags)}\n"
            
            preview += f"\n*Should I save this?* (yes/no)"
        
        elif session.intent in ["task_create", "task.create"]:
            title = session.collected_data.get("title", session.original_message)
            due_date = session.collected_data.get("due_date", "Not specified")
            priority = session.collected_data.get("priority", "medium")
            
            preview = (
                f"📋 *I'll create this task:*\n\n"
                f"*Task:* {title}\n"
                f"*Due:* {due_date}\n"
                f"*Priority:* {priority}\n"
                f"\n*Should I create this task?* (yes/no)"
            )
        
        elif session.intent == "list_manage":
            # Extract list items from content or title
            content = session.collected_data.get("content", "")
            title = session.collected_data.get("title", "")
            list_name = session.collected_data.get("list_name", "")
            
            # Parse items - could be comma-separated, "y"/"and" separated, etc.
            import re
            items_text = content if content else title
            # Split by comma, "y", "and"
            items = re.split(r'[,;]|\s+y\s+|\s+and\s+', items_text)
            items = [item.strip() for item in items if item.strip()]
            
            # Try to infer list name from title/content if not explicit
            if not list_name:
                # Check if title looks like a list name
                if title and ("lista" in title.lower() or "list" in title.lower()):
                    list_name = title
                else:
                    # Infer from content
                    if "compra" in items_text.lower() or "shopping" in items_text.lower():
                        list_name = "lista de la compra"
                    elif "grocery" in items_text.lower() or "groceries" in items_text.lower():
                        list_name = "grocery list"
                    else:
                        list_name = "list"
            
            # Build preview
            if len(items) == 1:
                preview = (
                    f"🛒 *I'll add to your {list_name}:*\n\n"
                    f"*Item:* {items[0]}\n"
                    f"\n*Should I add this?* (yes/no)"
                )
            else:
                items_list = "\n".join([f"  • {item}" for item in items])
                preview = (
                    f"🛒 *I'll add {len(items)} items to your {list_name}:*\n\n"
                    f"{items_list}\n"
                    f"\n*Should I add these?* (yes/no)"
                )
            
            # Store parsed items for later
            session.collected_data["parsed_items"] = items
            session.collected_data["list_name"] = list_name
        
        else:
            # Generic preview
            preview = (
                f"*I'll save:* {session.original_message[:100]}\n\n"
                f"*Proceed?* (yes/no)"
            )
        
        session.preview_message = preview
        session.state = ConversationState.AWAITING_CONFIRMATION
        
        print(f"✓ Preview generated")
        print(f"✓ Awaiting user confirmation...")
        
        await update.message.reply_text(preview, parse_mode="Markdown")
    
    async def _execute_list_add(
        self, session, chat_id: str, user_id: str, update: Update
    ) -> None:
        """Execute list add with multiple items."""
        from app.tools.list_tool import ListTool
        
        print(f"\n⚡ PHASE 3: Adding Items to List")
        print(f"{'─'*80}")
        
        items = session.collected_data.get("parsed_items", [])
        list_name = session.collected_data.get("list_name", "list")
        
        print(f"  ├─ List: {list_name}")
        print(f"  ├─ Items: {len(items)}")
        
        try:
            list_tool = ListTool()
            added_count = 0
            
            for item in items:
                try:
                    await list_tool.execute({
                        "operation": "add_item",
                        "list_name": list_name,
                        "item_text": item,
                        "user_id": user_id,
                        "chat_id": chat_id,
                    })
                    added_count += 1
                    print(f"  ├─ ✓ Added: {item}")
                except Exception as e:
                    print(f"  ├─ ✗ Failed: {item} ({e})")
            
            print(f"  └─ Complete: {added_count}/{len(items)} items added")
            
            if added_count == len(items):
                if added_count == 1:
                    response = f"✅ Added **{items[0]}** to your {list_name}!"
                else:
                    response = f"✅ Added {added_count} items to your {list_name}!"
            elif added_count > 0:
                response = f"⚠️ Added {added_count} out of {len(items)} items to your {list_name}."
            else:
                response = f"❌ Failed to add items to your {list_name}. Please try again."
            
            await update.message.reply_text(response, parse_mode="Markdown")
            
        except Exception as e:
            print(f"  ❌ List add failed: {str(e)}")
            logger.error("list_add_error", extra={"error": str(e), "chat_id": chat_id})
            await update.message.reply_text(
                f"I encountered an error while adding items. Please try again.\n\nError: {str(e)}"
            )

    async def _execute_capture(
        self, session, chat_id: str, user_id: str, update: Update
    ) -> None:
        """Execute the capture action."""
        print(f"\n⚡ PHASE 3: Executing Capture")
        print(f"{'─'*80}")
        
        try:
            capture_context = CaptureContext(
                chat_id=chat_id,
                user_id=user_id,
                auto_approve=True,  # Already confirmed by user
                approval_callback=None,
                clarification_callback=None,
            )
            
            result: CaptureResult = await self.capture_crew.capture(
                user_input=session.original_message,
                context=capture_context,
            )
            
            print(f"  ✓ Capture complete")
            print(f"  ✓ Actions executed: {result.actions_executed}")
            print(f"  ✓ Summary: {result.summary}")
            
            # Format response
            if result.summary:
                response = f"✅ {result.summary}"
            else:
                response = "✅ Done! I've saved that for you."
            
            await update.message.reply_text(response)
        
        except Exception as e:
            print(f"  ❌ Capture failed: {str(e)}")
            logger.error("capture_error", extra={"error": str(e), "chat_id": chat_id})
            await update.message.reply_text(
                f"I encountered an error while saving. Please try again.\n\nError: {str(e)}"
            )
    
    async def _handle_list_query(
        self, update: Update, text: str, chat_id: str, user_id: str
    ) -> None:
        """Handle queries about list contents."""
        from .question_detection import extract_list_name
        from app.tools.list_tool import ListTool
        
        print(f"  🛒 Querying list tool...")
        
        # Extract list name from query
        list_name = extract_list_name(text)
        if not list_name:
            # Default to "lista de la compra" / "shopping list" if ambiguous
            if "compra" in text.lower() or "shopping" in text.lower():
                list_name = "lista de la compra"
            else:
                list_name = None
        
        print(f"  ✓ List name: {list_name or 'all lists'}")
        
        try:
            # Get list tool
            list_tool = ListTool()
            
            if list_name:
                # Query specific list
                result = await list_tool.execute({
                    "operation": "list_items",
                    "list_name": list_name,
                })
                
                if result["count"] == 0:
                    response = f"🛒 Your **{list_name}** is empty."
                else:
                    response = f"🛒 **{list_name.title()}**:\n\n"
                    for item in result["items"]:
                        status = "✅" if item["completed"] else "⬜"
                        response += f"{status} {item['text']}\n"
                    response += f"\n_{result['count']} item(s) total_"
            else:
                # Show all lists
                result = await list_tool.execute({
                    "operation": "get_lists",
                    "user_id": user_id,
                    "chat_id": chat_id,
                })
                
                if result["count"] == 0:
                    response = "You don't have any lists yet."
                else:
                    response = f"📋 **Your Lists** ({result['count']}):\n\n"
                    for lst in result["lists"]:
                        response += f"• {lst['name']}\n"
            
            await update.message.reply_text(response, parse_mode="Markdown")
            
        except ValueError as e:
            # List not found
            if "not found" in str(e).lower():
                response = f"I couldn't find a list named **{list_name}**.\n\nTry: 'Add [item] to the {list_name}' to create it first."
                await update.message.reply_text(response, parse_mode="Markdown")
            else:
                raise
        
        except Exception as e:
            print(f"  ❌ List query error: {e}")
            await update.message.reply_text(
                "Sorry, I had trouble querying your lists. Please try again."
            )

    async def _execute_retrieval(
        self, chat_id: str, user_id: str, text: str, update: Update
    ) -> None:
        """Execute retrieval query."""
        print(f"  🔍 Searching memories...")
        
        try:
            retrieval_context = RetrievalContext(
                chat_id=chat_id,
                user_id=user_id,
                memory_service=self.memory_service,
            )
            
            result: RetrievalResult = self.retrieval_crew.retrieve(
                user_question=text,
                context=retrieval_context,
            )
            
            print(f"  ✓ Found {len(result.memories)} relevant memories")
            print(f"  ✓ Confidence: {result.answer.confidence:.2%}")
            print(f"  ✓ Answer: {result.answer.answer[:100]}...")
            
            # Format response
            response = f"💭 *What I found:*\n{result.answer.answer}\n"
            
            if result.answer.citations:
                response += f"\n*Sources:*\n"
                for idx, citation in enumerate(result.answer.citations[:3], 1):
                    response += f"{idx}. {citation.title}\n"
            
            if result.answer.confidence < 0.5:
                response += "\n⚠️ _I'm not very confident in this answer._"
            
            await update.message.reply_text(response, parse_mode="Markdown")
        
        except Exception as e:
            print(f"  ❌ Retrieval failed: {str(e)}")
            logger.error("retrieval_error", extra={"error": str(e), "chat_id": chat_id})
            await update.message.reply_text(
                "I couldn't find a good answer in my memory. Maybe I need more context?"
            )

    async def _handle_retrieval_query(
        self, chat_id: str, user_id: str, text: str, decision, update: Update
    ) -> None:
        """Route question to RetrievalCrew."""
        print(f"  🔍 Searching memories...")
        
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
            
            print(f"  ✓ Found {len(result.memories)} relevant memories")
            print(f"  ✓ Confidence: {result.answer.confidence:.2%}")
            print(f"  ✓ Answer: {result.answer.answer[:100]}...")
            
            # Format response
            response = f"� *What I found:*\n{result.answer.answer}\n"
            
            if result.answer.citations:
                response += f"\n*Sources:*\n"
                for idx, citation in enumerate(result.answer.citations[:3], 1):
                    response += f"{idx}. {citation.title}\n"
            
            if result.answer.confidence < 0.5:
                response += "\n⚠️ _I'm not very confident in this answer._"
            
            await update.message.reply_text(response, parse_mode="Markdown")
        
        except Exception as e:
            print(f"  ❌ Retrieval failed: {str(e)}")
            logger.error("retrieval_error", extra={"error": str(e), "chat_id": chat_id})
            await update.message.reply_text(
                "I couldn't find a good answer in my memory. Maybe I need more context?"
            )

    async def _handle_capture_action(
        self, chat_id: str, user_id: str, text: str, decision, update: Update
    ) -> None:
        """Route action to CaptureCrew."""
        print(f"  📝 Processing action...")
        
        try:
            # Create capture context with callbacks
            # Note: auto_approve=True to avoid async deadlock with approval flow
            # TODO: Implement proper async approval mechanism
            capture_context = CaptureContext(
                chat_id=chat_id,
                user_id=user_id,
                auto_approve=True,  # Auto-approve for now to avoid deadlock
                approval_callback=None,  # Disabled for now
                clarification_callback=None,  # Disabled for now
            )
            
            # Call CaptureCrew
            result: CaptureResult = await self.capture_crew.capture(
                user_input=text,
                context=capture_context,
            )
            
            print(f"  ✓ Capture complete")
            print(f"  ✓ Actions executed: {result.actions_executed}")
            print(f"  ✓ Summary: {result.summary}")
            
            # Format response
            if result.summary:
                response = f"✅ {result.summary}"
            else:
                response = "✅ Done! I've saved that for you."
            
            await update.message.reply_text(response)
        
        except Exception as e:
            print(f"  ❌ Capture failed: {str(e)}")
            logger.exception("capture_error", extra={"error": str(e), "chat_id": chat_id, "traceback": True})
            await update.message.reply_text(
                f"I had trouble saving that. Could you try again?\n\nError: {str(e)}"
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
