"""Capture Crew - Main orchestration for capturing user input.

The Capture Crew coordinates the PlannerAgent, ClarifierAgent, and ToolCallerAgent
to process user input, gather missing information, and execute tool actions.
"""

import os
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from crewai import Crew, Process

from app.config import get_settings
from app.contracts.plan import Plan
from app.contracts.tools import ToolResult
from app.crews.capture.clarifier import (
    ask_clarifications,
    create_clarifier_agent,
    update_plan_with_answers,
)
from app.crews.capture.planner import create_planner_agent, plan_from_input
from app.crews.capture.tool_caller import (
    create_tool_caller_agent,
    execute_plan_actions,
    format_results_summary,
)
from app.llm.crewai_llm import get_crewai_llm
from app.memory.api import MemoryService
from app.tracing import get_tracer

logger = get_tracer()


@dataclass
class CaptureContext:
    """Context for a capture session."""

    chat_id: str
    user_id: str
    auto_approve: bool = False
    approval_callback: Callable[[str, dict[str, Any]], bool] | None = None
    clarification_callback: Callable[[list[str]], dict[str, str]] | None = None


@dataclass
class CaptureResult:
    """Result of a capture operation."""

    plan: Plan
    results: list[ToolResult]
    summary: str
    clarifications_asked: int
    actions_executed: int


class CaptureCrew:
    """Capture Crew orchestrator.

    Manages the full capture workflow:
    1. Planning: Analyze user input → produce Plan
    2. Clarification: Ask for missing required info (max 3 questions)
    3. Execution: Execute tool actions with approval gates
    """

    def __init__(
        self,
        memory_service: MemoryService | None = None,
        llm=None,
    ):
        """Initialize the Capture Crew.

        Args:
            memory_service: Optional memory service for conversation context
            llm: Optional LLM configuration
        """
        self.memory_service = memory_service or MemoryService()
        self.llm = llm
        
        # CrewAI components (lazy initialization)
        self._agents_initialized = False
        self.planner_agent = None
        self.clarifier_agent = None
        self.tool_caller_agent = None
        self._crew = None
    
    def _initialize_agents(self):
        """Lazy initialization of CrewAI agents with shared memory.
        
        This is called on first use to avoid initialization overhead
        until actually needed.
        """
        if self._agents_initialized:
            return
        
        logger.info("Initializing CrewAI agents for CaptureCrew")
        
        # Get CrewAI-compatible LLM
        crewai_llm = get_crewai_llm(self.llm)
        logger.info("CrewAI LLM obtained successfully")
        
        # Get tools from registry and wrap them for CrewAI
        from app.tools.registry import get_registry
        from app.crews.capture.tool_wrapper import wrap_tool_for_crewai
        
        registry = get_registry()
        
        # Get all available tools from the registry
        tool_names = ["memory_note_tool", "task_tool", "list_tool", "temporal_tool"]
        
        crewai_tools = []
        for tool_name in tool_names:
            base_tool = registry.get(tool_name)
            if base_tool:
                crewai_tool = wrap_tool_for_crewai(base_tool)
                crewai_tools.append(crewai_tool)
                logger.info(f"Wrapped tool {tool_name} for CrewAI")
            else:
                logger.warning(f"Tool {tool_name} not found in registry")
        
        logger.info(f"Wrapped {len(crewai_tools)} tools for CrewAI agent")
        
        # Create agents with CrewAI LLM
        self.planner_agent = create_planner_agent(crewai_llm)
        self.clarifier_agent = create_clarifier_agent(crewai_llm)
        self.tool_caller_agent = create_tool_caller_agent(crewai_llm, tools=crewai_tools)
        logger.info("CrewAI agents created successfully")
        
        # Configure Ollama embeddings for CrewAI memory (use Ollama instead of OpenAI)
        # CrewAI expects specific environment variable format
        settings = get_settings()
        os.environ["EMBEDDINGS_OLLAMA_MODEL_NAME"] = "nomic-embed-text"
        os.environ["EMBEDDINGS_OLLAMA_BASE_URL"] = settings.ollama_base_url
        
        embedder_config = {
            "provider": "ollama",
            "config": {
                "model": "nomic-embed-text"
            }
        }
        
        # Create CrewAI Crew with shared memory and custom embeddings
        self._crew = Crew(
            agents=[self.planner_agent, self.clarifier_agent, self.tool_caller_agent],
            memory=settings.crewai_enable_memory,
            embedder=embedder_config,
            process=Process.sequential,
            verbose=True,
            full_output=True
        )
        
        logger.info("CrewAI crew initialized successfully")
        self._agents_initialized = True

    async def capture(
        self,
        user_input: str,
        context: CaptureContext,
    ) -> CaptureResult:
        """Process user input through the capture workflow.

        Args:
            user_input: Raw user input to process
            context: Capture context with chat/user IDs and callbacks

        Returns:
            CaptureResult with plan, execution results, and summary
        """
        # Step 1: Planning
        print(f"    ├─ Planning...")
        await self._get_conversation_context(context.chat_id)

        plan = plan_from_input(
            user_input=user_input,
            chat_id=context.chat_id,
            user_id=context.user_id,
            llm=self.llm,
        )

        print(f"    ├─ Plan: {plan.intent} ({plan.confidence:.0%} confidence)")
        print(f"    ├─ Actions: {len(plan.actions)}")

        # Step 2: Clarification (if needed)
        clarifications_asked = 0

        if plan.followups:
            print(f"    ├─ Clarifying ({len(plan.followups)} questions)...")
            answers = await self._handle_clarifications(plan, context)
            clarifications_asked = len(answers)

            if answers:
                plan = update_plan_with_answers(plan, answers)
                print(f"    ├─ Clarified: {len(answers)} answers received")

        # Step 3: Execution
        print(f"    └─ Executing actions...")
        results = await execute_plan_actions(
            plan=plan,
            chat_id=context.chat_id,
            user_id=context.user_id,
            auto_approve=context.auto_approve,
            approval_callback=context.approval_callback,
        )

        # Generate summary
        summary = format_results_summary(results)

        # Save to conversation memory
        await self._save_to_memory(user_input, plan, results, context)

        return CaptureResult(
            plan=plan,
            results=results,
            summary=summary,
            clarifications_asked=clarifications_asked,
            actions_executed=len(results),
        )

    async def _get_conversation_context(self, chat_id: str) -> list[dict]:
        """Get recent conversation context from memory.

        Args:
            chat_id: Chat identifier

        Returns:
            List of recent messages
        """
        try:
            # Get last 5 messages for context
            history = self.memory_service.stm.get_history(chat_id=chat_id, limit=5)
            return [
                {"role": msg.role, "content": msg.content}
                for msg in history
            ]
        except Exception as e:
            logger.warning(
                "capture.context_error",
                extra={"error": str(e), "chat_id": chat_id},
            )
            return []

    async def _handle_clarifications(
        self, plan: Plan, context: CaptureContext
    ) -> dict[str, str]:
        """Handle clarification questions.

        Args:
            plan: Plan with followup questions
            context: Capture context with callback

        Returns:
            Dictionary of field -> answer
        """
        # Get questions to ask
        questions = await ask_clarifications(
            plan=plan,
            chat_id=context.chat_id,
            user_id=context.user_id,
            llm=self.llm,
        )

        # If there's a callback, use it to get actual answers
        if context.clarification_callback:
            try:
                answers = await context.clarification_callback(plan.followups)
                return answers
            except Exception as e:
                logger.error(
                    "capture.clarification_error",
                    extra={"error": str(e), "chat_id": context.chat_id},
                )
                return {}

        # No callback - return empty answers
        return questions

    async def _save_to_memory(
        self,
        user_input: str,
        plan: Plan,
        results: list[ToolResult],
        context: CaptureContext,
    ):
        """Save capture interaction to memory.

        Args:
            user_input: Original user input
            plan: Generated plan
            results: Tool execution results
            context: Capture context
        """
        try:
            # Save user message
            self.memory_service.stm.add_message(
                chat_id=context.chat_id,
                role="user",
                content=user_input,
            )

            # Save assistant response with summary
            summary = format_results_summary(results)
            self.memory_service.stm.add_message(
                chat_id=context.chat_id,
                role="assistant",
                content=summary,
            )

            logger.debug(
                "capture.memory_saved",
                extra={"chat_id": context.chat_id},
            )

        except Exception as e:
            logger.error(
                "capture.memory_error",
                extra={"error": str(e), "chat_id": context.chat_id},
            )
    
    async def capture_with_crew_tasks(
        self,
        user_input: str,
        context: CaptureContext,
    ) -> CaptureResult:
        """Process user input using Hybrid approach (Agent Planning + Code Execution).
        
        REPLACED: The pure CrewAI implementation was unreliable for tool execution.
        Now uses:
        1. plan_from_input (LLM/Agent) -> Structured Plan
        2. execute_plan_actions (Python) -> Reliable Tool Execution
        """
        logger.info("Using Hybrid Capture Flow (Plan -> Code Execution)")
        
        # Redirect to the robust capture implementation that uses 
        # plan_from_input() + execute_plan_actions()
        return await self.capture(user_input, context)
