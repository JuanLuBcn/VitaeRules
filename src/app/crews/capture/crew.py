"""Capture Crew - Main orchestration for capturing user input.

The Capture Crew coordinates the PlannerAgent, ClarifierAgent, and ToolCallerAgent
to process user input, gather missing information, and execute tool actions.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.contracts.plan import Plan
from app.contracts.tools import ToolResult
from app.crews.capture.clarifier import (
    ask_clarifications,
    update_plan_with_answers,
)
from app.crews.capture.planner import plan_from_input
from app.crews.capture.tool_caller import (
    execute_plan_actions,
    format_results_summary,
)
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
