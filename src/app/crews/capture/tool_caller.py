"""Tool Caller Agent for the Capture Crew.

The ToolCallerAgent takes a finalized Plan, renders ToolCalls,
handles user approvals for side-effecting operations, and executes tools.
"""

from uuid import uuid4

from crewai import Agent

from app.contracts.plan import Plan
from app.contracts.tools import ToolCall, ToolResult, ToolStatus
from app.tools.registry import get_registry
from app.tracing import get_tracer

logger = get_tracer()


def create_tool_caller_agent(llm=None) -> Agent:
    """Create the Tool Caller Agent.

    Args:
        llm: Optional LLM configuration. If None, uses CrewAI defaults.

    Returns:
        CrewAI Agent configured for tool execution.
    """
    agent_config = {
        "role": "Tool Executor",
        "goal": (
            "Execute planned tool actions safely, requesting approval for "
            "side-effecting operations and handling errors gracefully"
        ),
        "backstory": (
            "You are a precise executor of tool operations. You convert plans into "
            "actual tool calls, validate parameters, request user confirmation for "
            "destructive or side-effecting actions, and handle errors with clear "
            "explanations. You never modify data without approval. You provide "
            "concise summaries of what was done."
        ),
        "verbose": True,
        "allow_delegation": False,
    }

    if llm:
        agent_config["llm"] = llm

    return Agent(**agent_config)


def requires_approval(tool_name: str, operation: str | None = None) -> bool:
    """Check if a tool operation requires user approval.

    Args:
        tool_name: Name of the tool
        operation: Specific operation (if applicable)

    Returns:
        True if approval is required
    """
    # Define tools/operations that are side-effecting
    side_effecting = {
        "task_tool": ["delete_task"],
        "list_tool": ["delete_list"],
        "memory_note_tool": [],  # All memory writes should be approved
    }

    # Check if tool requires approval
    if tool_name in side_effecting:
        if not side_effecting[tool_name]:
            # Empty list means all operations require approval
            return True
        if operation and operation in side_effecting[tool_name]:
            return True

    return False


async def execute_plan_actions(
    plan: Plan,
    chat_id: str = "default",
    user_id: str = "user",
    auto_approve: bool = False,
    approval_callback=None,
) -> list[ToolResult]:
    """Execute all tool actions from a plan.

    Args:
        plan: Finalized plan with actions
        chat_id: Chat identifier
        user_id: User identifier
        auto_approve: If True, skip approval prompts (for testing)
        approval_callback: Function to request approval (tool_name, params) -> bool

    Returns:
        List of ToolResult objects
    """
    if not plan.actions:
        logger.debug(
            "tool_caller.skip", extra={"reason": "no_actions", "chat_id": chat_id}
        )
        return []

    # Check safety
    if plan.safety.blocked:
        logger.warning(
            "tool_caller.blocked",
            extra={"reason": plan.safety.reason, "chat_id": chat_id},
        )
        return [
            ToolResult(
                call_id=uuid4(),
                tool_name="system",
                status=ToolStatus.ERROR,
                error=f"Plan blocked: {plan.safety.reason}",
                duration_ms=0,
            )
        ]

    registry = get_registry()
    results = []

    logger.info(
        "tool_caller.start",
        extra={"action_count": len(plan.actions), "chat_id": chat_id},
    )

    for idx, action in enumerate(plan.actions):
        logger.debug(
            "tool_caller.action",
            extra={
                "index": idx,
                "tool": action.tool,
                "params": action.params,
                "chat_id": chat_id,
            },
        )

        # Check if approval is required
        operation = action.params.get("operation")
        needs_approval = requires_approval(action.tool, operation)

        if needs_approval and not auto_approve:
            # Request approval
            approved = False

            if approval_callback:
                try:
                    approved = await approval_callback(action.tool, action.params)
                except Exception as e:
                    logger.error(
                        "tool_caller.approval_error",
                        extra={"error": str(e), "chat_id": chat_id},
                    )
                    approved = False
            else:
                # No callback provided - log and skip
                logger.warning(
                    "tool_caller.no_approval_callback",
                    extra={"tool": action.tool, "chat_id": chat_id},
                )
                approved = False

            if not approved:
                logger.info(
                    "tool_caller.denied",
                    extra={"tool": action.tool, "chat_id": chat_id},
                )
                results.append(
                    ToolResult(
                        call_id=uuid4(),
                        tool_name=action.tool,
                        status=ToolStatus.ERROR,
                        error="User denied approval",
                        duration_ms=0,
                    )
                )
                continue

        # Execute the tool
        try:
            # Add context to params
            params_with_context = {
                **action.params,
                "chat_id": chat_id,
                "user_id": user_id,
            }

            # Create tool call
            tool_call = ToolCall(
                tool_name=action.tool,
                arguments=params_with_context,
                correlation_id=chat_id,
            )

            # Execute via registry
            result = await registry.execute(tool_call)
            results.append(result)

            logger.info(
                "tool_caller.executed",
                extra={
                    "tool": action.tool,
                    "status": result.status,
                    "duration_ms": result.duration_ms,
                    "chat_id": chat_id,
                },
            )

        except Exception as e:
            logger.error(
                "tool_caller.error",
                extra={"tool": action.tool, "error": str(e), "chat_id": chat_id},
            )
            results.append(
                ToolResult(
                    call_id=uuid4(),
                    tool_name=action.tool,
                    status=ToolStatus.ERROR,
                    error=str(e),
                    duration_ms=0,
                )
            )

    logger.info(
        "tool_caller.complete",
        extra={
            "total_actions": len(plan.actions),
            "successful": sum(1 for r in results if r.status == ToolStatus.SUCCESS),
            "failed": sum(1 for r in results if r.status == ToolStatus.ERROR),
            "chat_id": chat_id,
        },
    )

    return results


def format_results_summary(results: list[ToolResult]) -> str:
    """Format tool execution results into a user-friendly summary.

    Args:
        results: List of tool results

    Returns:
        Human-readable summary string
    """
    if not results:
        return "No actions were executed."

    successful = [r for r in results if r.status == ToolStatus.SUCCESS]
    failed = [r for r in results if r.status == ToolStatus.ERROR]

    summary_parts = []

    if successful:
        summary_parts.append(f"✅ {len(successful)} action(s) completed successfully")

    if failed:
        summary_parts.append(f"❌ {len(failed)} action(s) failed")
        for result in failed[:3]:  # Show first 3 errors
            if result.error:
                summary_parts.append(f"  - {result.error}")

    return "\n".join(summary_parts)
