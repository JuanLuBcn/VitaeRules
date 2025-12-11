"""Chat Crew - Natural conversational interface with intelligent delegation.

The Chat Crew handles user conversations, determines when to search for information
or execute actions, and delegates to specialized crews as needed.
"""

import os
import time
from dataclasses import dataclass
from enum import Enum

from crewai import Crew, Process

from app.config import get_settings
from app.crews.chat.chat_agent import create_chat_agent
from app.crews.chat.intent_analyzer import create_intent_analyzer_agent
from app.crews.chat.response_composer import create_response_composer_agent
from app.crews.search.crew import SearchContext
from app.llm.crewai_llm import get_crewai_llm
from app.memory.api import MemoryService
from app.tracing import get_tracer

logger = get_tracer()


class ConversationIntent(str, Enum):
    """Types of conversation intents.
    
    Binary classification:
    - SEARCH: Retrieve/query existing information
    - ACTION: Store/modify data or communicate (default)
    """

    SEARCH = "search"  # Search for stored information
    ACTION = "action"  # Execute an action or store data (default)


@dataclass
class ChatContext:
    """Context for a chat interaction."""

    chat_id: str
    user_id: str
    conversation_history: list[dict] = None  # Previous messages


@dataclass
class ChatResponse:
    """Response from a chat interaction."""

    message: str
    intent: ConversationIntent
    searched: bool = False  # Whether we delegated to search crew
    acted: bool = False  # Whether we delegated to capture crew
    sources: list[str] = None  # Data sources used (if searched)


class ChatCrew:
    """Chat Crew orchestrator.

    Manages conversational interactions:
    1. Intent Analysis: Determine if user wants to chat, search, or act
    2. Delegation: Route to UnifiedSearchCrew or CaptureCrew if needed
    3. Response: Compose natural, context-aware response
    """

    def __init__(
        self,
        memory_service: MemoryService | None = None,
        search_crew=None,  # UnifiedSearchCrew for information retrieval
        capture_crew=None,  # CaptureCrew for action execution
        llm=None,
    ):
        """Initialize the Chat Crew.

        Args:
            memory_service: Memory service for conversation history
            search_crew: UnifiedSearchCrew for searching information
            capture_crew: CaptureCrew for executing actions
            llm: Optional LLM configuration
        """
        self.memory_service = memory_service or MemoryService()
        self.search_crew = search_crew
        self.capture_crew = capture_crew
        self.llm = llm

        # CrewAI components (lazy initialization)
        self._agents_initialized = False
        self.intent_analyzer_agent = None
        self.chat_agent = None
        self.response_composer_agent = None
        self._crew = None

    def _initialize_agents(self):
        """Lazy initialization of CrewAI agents with shared memory.

        This is called on first use to avoid initialization overhead
        until actually needed.
        """
        if self._agents_initialized:
            return

        logger.info("Initializing CrewAI agents for ChatCrew")

        # Get CrewAI-compatible LLM
        crewai_llm = get_crewai_llm(self.llm)
        logger.info("CrewAI LLM obtained successfully")

        # Create agents with CrewAI LLM
        self.intent_analyzer_agent = create_intent_analyzer_agent(crewai_llm)
        self.chat_agent = create_chat_agent(crewai_llm)
        self.response_composer_agent = create_response_composer_agent(crewai_llm)
        logger.info("CrewAI agents created successfully")

        # Configure Ollama embeddings for CrewAI memory (use Ollama instead of OpenAI)
        settings = get_settings()
        os.environ["EMBEDDINGS_OLLAMA_MODEL_NAME"] = "nomic-embed-text"
        os.environ["EMBEDDINGS_OLLAMA_BASE_URL"] = settings.ollama_base_url

        embedder_config = {
            "provider": "ollama",
            "config": {"model": "nomic-embed-text"},
        }

        # Create CrewAI Crew with shared memory and custom embeddings
        self._crew = Crew(
            agents=[
                self.intent_analyzer_agent,
                self.chat_agent,
                self.response_composer_agent,
            ],
            memory=settings.crewai_enable_memory,
            embedder=embedder_config,
            process=Process.sequential,
            verbose=True,
            full_output=True,
        )

        logger.info("CrewAI crew initialized successfully")
        self._agents_initialized = True

    async def chat_with_crew_tasks(
        self,
        user_message: str,
        context: ChatContext,
    ) -> ChatResponse:
        """Process user message using CrewAI orchestration with shared memory.

        This method uses CrewAI's task-based workflow where agents collaborate:
        1. IntentAnalyzer determines intent (chat, search, or action)
        2. ChatAgent provides conversational response (or delegates)
        3. ResponseComposer creates final natural response

        Args:
            user_message: User's message
            context: Chat context with history and IDs

        Returns:
            ChatResponse with natural language response and metadata
        """
        from crewai import Task

        start_time = time.time()
        logger.info("🕐 [TIMING] Starting chat_with_crew_tasks")

        # Initialize agents if not already done
        init_start = time.time()
        self._initialize_agents()
        init_time = time.time() - init_start
        logger.info(f"🕐 [TIMING] Agent initialization took {init_time:.2f}s")

        logger.info("Starting crew.kickoff() for chat interaction")

        # Get conversation history summary for context
        history_summary = ""
        if context.conversation_history:
            recent = context.conversation_history[-3:]  # Last 3 messages
            history_summary = "\n".join(
                [
                    f"{msg['role']}: {msg['content']}"
                    for msg in recent
                ]
            )

        # Task 1: Intent Analysis - determine what user wants
        intent_task = Task(
            description=f"""Analyze this user message and determine the user's primary intent:

User message: "{user_message}"

Recent conversation history:
{history_summary if history_summary else "No previous messages"}

Classify the intent as ONE of these TWO categories based on semantic meaning:

**SEARCH**: The user wants to retrieve or query existing information
- Requesting information from stored data
- Asking about past events, conversations, or memories
- Inquiring about general knowledge
- The message is a question seeking an answer

**ACTION**: The user wants to store, create, modify, or communicate information (DEFAULT)
- Providing new information or describing events
- Giving commands to store, modify, or delete data
- Engaging in social interaction
- Sharing thoughts, feelings, or observations
- Any message that is NOT explicitly requesting information
- When uncertain, choose ACTION

Understand what the user fundamentally wants to accomplish:
- ASKING for information they don't have → SEARCH
- TELLING you something or expressing themselves → ACTION

Default to ACTION unless the message is clearly seeking information.

Output format:
Primary Intent: [SEARCH/ACTION]
Reasoning: [Brief explanation of your decision based on semantic analysis]""",
            agent=self.intent_analyzer_agent,
            expected_output="Intent classification (SEARCH or ACTION) with reasoning",
        )

        # Parse intent early to enable delegation
        # We'll execute intent_task first, then check result to decide on delegation
        logger.info("🕐 [TIMING] Starting intent analysis phase")
        intent_phase_start = time.time()
        
        self._crew.tasks = [intent_task]
        kickoff_start = time.time()
        logger.info("🕐 [TIMING] About to call crew.kickoff() for intent analysis")
        
        intent_result = self._crew.kickoff(
            inputs={
                "user_message": user_message,
                "chat_id": context.chat_id,
                "user_id": context.user_id,
                "history": history_summary,
            }
        )
        
        kickoff_time = time.time() - kickoff_start
        logger.info(f"🕐 [TIMING] Intent crew.kickoff() completed in {kickoff_time:.2f}s")
        
        intent_output = intent_result.raw if hasattr(intent_result, "raw") else str(intent_result)
        logger.info(f"Intent analysis result: {intent_output[:200]}")
        
        intent_phase_time = time.time() - intent_phase_start
        logger.info(f"🕐 [TIMING] Total intent analysis phase: {intent_phase_time:.2f}s")
        
        # Determine if we need to delegate
        searched_results = None
        action_results = None
        
        # Binary intent detection - SEARCH or ACTION (default)
        intent_output_upper = intent_output.upper()
        
        # Check for SEARCH keywords (more specific, check first)
        if any(keyword in intent_output_upper for keyword in [
            "PRIMARY INTENT: SEARCH",
            "INTENT: SEARCH",
            "**SEARCH**",
            "CLASSIFICATION: SEARCH",
        ]) or (
            "SEARCH" in intent_output_upper and 
            any(word in intent_output_upper for word in ["WHAT", "WHEN", "WHERE", "WHO", "HOW", "WHY", "FIND", "SHOW", "LIST"])
        ):
            intent = ConversationIntent.SEARCH
            logger.info(f"SEARCH intent detected in output: {intent_output[:100]}")
        else:
            # Default to ACTION for everything else
            intent = ConversationIntent.ACTION
            logger.info(f"ACTION intent detected (default): {intent_output[:100]}")
        
        # Now perform delegation based on detected intent
        if intent == ConversationIntent.SEARCH:
            logger.info("Delegating to UnifiedSearchCrew")
            
            # Actually delegate to UnifiedSearchCrew
            if self.search_crew:
                try:
                    search_context = SearchContext(
                        user_id=context.user_id,
                        chat_id=context.chat_id,
                        sources=None,  # Search all sources
                    )
                    search_response = await self.search_crew.search_with_crew_tasks(
                        query=user_message,
                        context=search_context
                    )
                    # SearchResult has combined_summary, not results
                    searched_results = search_response.combined_summary
                    logger.info(f"Search completed with {search_response.total_results} total results")
                except Exception as e:
                    logger.error(f"Search delegation failed: {e}")
                    searched_results = f"Search error: {str(e)}"
        
        elif intent == ConversationIntent.ACTION:
            logger.info("Delegating to CaptureCrew")
            
            # Actually delegate to CaptureCrew
            if self.capture_crew:
                try:
                    from app.crews.capture.crew import CaptureContext
                    
                    capture_context = CaptureContext(
                        chat_id=context.chat_id,
                        user_id=context.user_id,
                        auto_approve=True,  # Auto-approve for now
                    )
                    capture_response = await self.capture_crew.capture_with_crew_tasks(
                        user_input=user_message,
                        context=capture_context,
                    )
                    action_results = capture_response.summary
                    logger.info(f"Action completed: {action_results[:100]}")
                except Exception as e:
                    logger.error(f"Action delegation failed: {e}")
                    action_results = f"Action error: {str(e)}"

        # Task 2: Response Composition - format delegation results
        # Note: With binary SEARCH/ACTION architecture, we ALWAYS delegate
        # So this task just formats the results from the delegated crew
        delegation_info = ""
        if searched_results:
            delegation_info = f"\n\nSearch results from UnifiedSearchCrew:\n{searched_results}"
        elif action_results:
            delegation_info = f"\n\nAction result from CaptureCrew:\n{action_results}"
        
        chat_task = Task(
            description=f"""Based on the intent analysis, handle the user's message:

User message: "{user_message}"
Intent from previous analysis: {intent.value.upper()}
{delegation_info}

If SEARCH:
- Integrate the search results naturally into your response
- Cite the information found  
- Be helpful and informative
- If no results found, the search crew may have provided a general knowledge answer or asked for clarification

If ACTION:
- Confirm the action was completed (if tools were executed)
- Summarize what was done
- If no action was needed (trivial message), provide a conversational response
- Offer to help with anything else

Provide a clear, helpful response appropriate to the intent.""",
            agent=self.chat_agent,
            context=[],  # Intent already analyzed
            expected_output="Natural language response appropriate to the intent",
        )

        # Task 3: Response Composition - create final polished response
        compose_task = Task(
            description=f"""Compose the final response to the user:

Original message: "{user_message}"
Intent: {intent.value.upper()}
Response: [From chat agent]
{delegation_info}

Create a natural, polished final response that:
1. Addresses the user's message appropriately
2. Maintains conversation flow and context
3. Is friendly, helpful, and clear
4. If SEARCH intent: integrate search results naturally
5. If ACTION intent: confirm what was completed (or respond conversationally if trivial)

Make the response concise but complete, warm but professional.""",
            agent=self.response_composer_agent,
            context=[chat_task],  # Read chat agent response
            expected_output="Final polished response ready to send to user",
        )

        # Set remaining tasks on the crew
        self._crew.tasks = [chat_task, compose_task]

        # Execute the crew workflow for chat and compose
        logger.info("🕐 [TIMING] Starting chat+compose phase")
        chat_compose_start = time.time()
        
        try:
            result = self._crew.kickoff(
                inputs={
                    "user_message": user_message,
                    "chat_id": context.chat_id,
                    "user_id": context.user_id,
                    "history": history_summary,
                    "intent": intent.value,
                }
            )

            chat_compose_time = time.time() - chat_compose_start
            logger.info(f"🕐 [TIMING] Chat+compose crew.kickoff() completed in {chat_compose_time:.2f}s")
            logger.info("Crew.kickoff() completed successfully for chat")

            # Parse final answer from CrewOutput
            final_answer = result.raw if hasattr(result, "raw") else str(result)

            # Save to conversation memory
            memory_start = time.time()
            self.memory_service.add_message(
                chat_id=context.chat_id,
                role="user",
                content=user_message,
            )
            self.memory_service.add_message(
                chat_id=context.chat_id,
                role="assistant",
                content=final_answer,
            )
            memory_time = time.time() - memory_start
            logger.info(f"🕐 [TIMING] Memory saving took {memory_time:.2f}s")
            
            total_time = time.time() - start_time
            logger.info(f"🕐 [TIMING] ⏰ TOTAL chat_with_crew_tasks: {total_time:.2f}s")

            return ChatResponse(
                message=final_answer,
                intent=intent,
                searched=bool(searched_results),
                acted=bool(action_results),
                sources=searched_results if searched_results else None,
            )

        except Exception as e:
            logger.error(
                "CrewAI kickoff failed for chat",
                extra={"error": str(e), "message": user_message},
            )
            raise
