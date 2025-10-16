"""Clarifier Agent for the Capture Crew.

The ClarifierAgent takes a Plan with followup questions and engages
the user to collect missing required information. Enforces max 3 questions.
"""

from crewai import Agent

from app.contracts.plan import Plan
from app.tracing import get_tracer

logger = get_tracer()


def create_clarifier_agent(llm=None) -> Agent:
    """Create the Clarifier Agent.

    Args:
        llm: Optional LLM configuration. If None, uses CrewAI defaults.

    Returns:
        CrewAI Agent configured for clarification.
    """
    agent_config = {
        "role": "Clarifier",
        "goal": (
            "Ask the user precise, focused questions to gather missing "
            "required information for tool execution"
        ),
        "backstory": (
            "You are an expert at asking clear, concise questions to fill in gaps. "
            "You never ask unnecessary questions - only when critical information is missing. "
            "You ask a maximum of 3 questions per interaction. You synthesize answers back "
            "into the original plan structure. You are brief and respectful of the user's time."
        ),
        "verbose": True,
        "allow_delegation": False,
    }

    if llm:
        agent_config["llm"] = llm

    return Agent(**agent_config)


async def ask_clarifications(
    plan: Plan, chat_id: str = "default", user_id: str = "user", llm=None
) -> dict[str, str]:
    """Ask clarification questions and collect answers.

    Args:
        plan: Plan with followup questions
        chat_id: Chat identifier
        user_id: User identifier
        llm: Optional LLM configuration

    Returns:
        Dictionary mapping field names to user answers
    """
    if not plan.followups:
        logger.debug(
            "clarifier.skip", extra={"reason": "no_followups", "chat_id": chat_id}
        )
        return {}

    # Enforce max 3 questions
    questions_to_ask = plan.followups[:3]

    if len(plan.followups) > 3:
        logger.warning(
            "clarifier.truncated",
            extra={
                "original_count": len(plan.followups),
                "asked_count": 3,
                "chat_id": chat_id,
            },
        )

    logger.info(
        "clarifier.start",
        extra={"question_count": len(questions_to_ask), "chat_id": chat_id},
    )

    # For MVP, we'll collect questions and return them for external handling
    # In a full implementation, this would interact with the user via the adapter
    answers = {}

    for followup in questions_to_ask:
        logger.debug("clarifier.question", extra={"field": followup.field, "ask": followup.ask})
        # In production, this would call out to the adapter/UI to get user input
        # For now, we'll just log and return empty (to be filled by caller)
        answers[followup.field] = None

    logger.info("clarifier.complete", extra={"answers_collected": len(answers)})
    return answers


def update_plan_with_answers(plan: Plan, answers: dict[str, str]) -> Plan:
    """Update plan entities with clarification answers.

    Args:
        plan: Original plan
        answers: Dictionary of field -> value mappings

    Returns:
        Updated plan with filled entities
    """
    # Create a copy of entities
    updated_entities = plan.entities.model_copy()

    # Map answers to entity fields
    for field, value in answers.items():
        if value is None:
            continue

        # Handle different field types
        if field == "priority":
            try:
                updated_entities.priority = int(value)
            except (ValueError, TypeError):
                logger.warning(
                    "clarifier.invalid_answer",
                    extra={"field": field, "value": value, "expected": "int"},
                )

        elif field in ["due_at", "happened_at"]:
            # Temporal fields - assume ISO format or will be parsed by TemporalTool
            setattr(updated_entities, field, value)

        elif field == "title":
            updated_entities.title = value

        elif field == "list_name":
            updated_entities.list_name = value

        elif field == "description":
            updated_entities.description = value

        elif field == "items":
            # Handle comma-separated items
            if isinstance(value, str):
                updated_entities.items = [
                    item.strip() for item in value.split(",") if item.strip()
                ]
            elif isinstance(value, list):
                updated_entities.items = value

        else:
            logger.warning(
                "clarifier.unknown_field", extra={"field": field, "value": value}
            )

    # Create updated plan
    updated_plan = plan.model_copy(update={"entities": updated_entities})

    # Clear followups since they've been addressed
    updated_plan.followups = []

    logger.info(
        "plan.updated",
        extra={"fields_updated": len(answers), "remaining_followups": 0},
    )

    return updated_plan
