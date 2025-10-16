"""Planner Agent for the Capture Crew.

The PlannerAgent analyzes user input and produces a structured Plan
containing intent, entities, required tool actions, and any clarifications needed.
"""

from crewai import Agent, Task

from app.contracts.plan import Plan
from app.tools.registry import get_registry
from app.tracing import get_tracer

logger = get_tracer()


def create_planner_agent(llm=None) -> Agent:
    """Create the Planner Agent.

    Args:
        llm: Optional LLM configuration. If None, uses CrewAI defaults.

    Returns:
        CrewAI Agent configured for planning.
    """
    agent_config = {
        "role": "Capture Planner",
        "goal": (
            "Analyze user input and produce a structured plan with intent, "
            "extracted entities, and proposed tool actions"
        ),
        "backstory": (
            "You are an expert at understanding user intentions and breaking them down "
            "into actionable steps. You identify what the user wants to accomplish, "
            "extract relevant entities (dates, people, places), and determine which "
            "tools should be called. When information is missing, you note what needs "
            "to be clarified. You output structured JSON plans, never prose."
        ),
        "verbose": True,
        "allow_delegation": False,
    }

    if llm:
        agent_config["llm"] = llm

    return Agent(**agent_config)


def create_planning_task(
    agent: Agent, user_input: str, chat_id: str, user_id: str
) -> Task:
    """Create a planning task.

    Args:
        agent: The planner agent
        user_input: Raw user input to analyze
        chat_id: Chat identifier
        user_id: User identifier

    Returns:
        CrewAI Task configured for planning.
    """
    # Get available tools from registry
    registry = get_registry()
    available_tools = registry.list_tools()

    tool_descriptions = "\n".join(
        [f"- {name}: {info['description']}" for name, info in available_tools.items()]
    )

    task_description = f"""Analyze this user input and create a structured plan:

User Input: {user_input}
Chat ID: {chat_id}
User ID: {user_id}

Available Tools:
{tool_descriptions}

Your task:
1. Identify the primary intent (task.create, list.add, memory.note, etc.)
2. Extract entities: dates, times, people, places, priorities, list names, items
3. Determine which tool(s) need to be called and with what parameters
4. If critical information is missing, add followup questions (max 3)
5. Check for safety issues (destructive operations, unclear intent)

Output a JSON Plan with this structure:
{{
    "intent": "task.create",  // IntentType enum value
    "entities": {{
        "title": "...",
        "due_at": "2025-10-17T15:00:00",  // ISO format
        "priority": 2,
        "items": ["item1", "item2"],
        "person_refs": ["@john"],
        "place_refs": ["Madrid"],
        "tags": ["work", "urgent"]
    }},
    "followups": [
        {{"ask": "What priority should this task have?", "field": "priority"}}
    ],
    "actions": [
        {{"tool": "task_tool", "params": {{"title": "...", "due_at": "..."}}}}
    ],
    "safety": {{"blocked": false, "reason": null}},
    "confidence": 0.9,
    "reasoning": "User wants to create a task with a specific due date..."
}}

Important:
- Use ISO 8601 format for dates/times
- Only propose actions if you have enough information
- Ask followup questions only for REQUIRED missing fields
- Set confidence based on how clear the input is
- Be concise in reasoning
"""

    return Task(
        description=task_description,
        agent=agent,
        expected_output="A JSON Plan object with intent, entities, actions, and followups",
    )


async def plan_from_input(
    user_input: str, chat_id: str = "default", user_id: str = "user", llm=None
) -> Plan:
    """Generate a Plan from user input.

    This is a convenience function that creates the agent and task,
    runs the planning, and returns a validated Plan object.

    Args:
        user_input: Raw user input
        chat_id: Chat identifier
        user_id: User identifier
        llm: Optional LLM configuration

    Returns:
        Validated Plan object
    """
    logger.debug("plan.start", extra={"user_input": user_input, "chat_id": chat_id})

    # Create agent and task
    agent = create_planner_agent(llm=llm)
    task = create_planning_task(agent, user_input, chat_id, user_id)

    # Execute task (CrewAI handles the LLM call)
    # Note: For now, we'll use a simplified approach
    # In a full Crew, this would be orchestrated by the Crew itself
    result = task.execute()

    # Parse result into Plan
    # TODO: Add proper JSON parsing and validation
    # For now, return a basic plan structure
    try:
        import json

        if isinstance(result, str):
            plan_data = json.loads(result)
        else:
            plan_data = result

        plan = Plan(**plan_data)
        logger.info(
            "plan.complete",
            extra={
                "intent": plan.intent,
                "confidence": plan.confidence,
                "action_count": len(plan.actions),
                "followup_count": len(plan.followups),
            },
        )
        return plan

    except Exception as e:
        logger.error("plan.parse_failed", extra={"error": str(e)})
        # Return a fallback unknown plan
        return Plan(
            intent="unknown",
            reasoning=f"Failed to parse plan: {e}",
            confidence=0.0,
        )
