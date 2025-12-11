"""Planner Agent for the Capture Crew.

The PlannerAgent analyzes user input and produces a structured Plan
containing intent, entities, required tool actions, and any clarifications needed.
"""

from crewai import Agent

from app.contracts.plan import Plan
from app.tools.registry import get_registry
from app.tracing import get_tracer
from app.llm import get_llm_service

logger = get_tracer()


def create_planner_agent(llm=None) -> Agent:
    """Create the Planner Agent.

    Args:
        llm: Optional LLM configuration. If None, uses CrewAI defaults.

    Returns:
        CrewAI Agent configured for intent analysis and action planning.
    """
    agent_config = {
        "role": "Action Planner",
        "goal": (
            "Analyze user input to identify intent, extract entities, "
            "determine required tool actions, and identify missing information"
        ),
        "backstory": (
            "You are an expert at understanding user requests and converting them into "
            "structured action plans. You classify intents precisely (task.create, "
            "list.add, memory.note, etc.), extract people, places, dates, and tags. "
            "You identify which tools need to be called and what parameters are required. "
            "You detect when critical information is missing and need clarification. "
            "You never block safe operations like creating notes, tasks, or reminders. "
            "You are thorough but efficient, producing complete plans with high confidence."
        ),
        "verbose": True,
        "allow_delegation": False,
    }

    if llm:
        agent_config["llm"] = llm

    return Agent(**agent_config)


def _build_planning_prompt(user_input: str, chat_id: str, user_id: str) -> str:
    """Build the planning prompt for the LLM.
    
    Args:
        user_input: Raw user input
        chat_id: Chat identifier
        user_id: User identifier
        
    Returns:
        Formatted prompt for LLM
    """
    # Get available tools with their full schemas
    registry = get_registry()
    available_tools = registry.list_tools()
    
    tool_descriptions = []
    for tool in available_tools:
        schema = tool.get('schema', {})
        required = schema.get('required', [])
        properties = schema.get('properties', {})
        
        # Build parameter list
        params = []
        for prop_name, prop_info in properties.items():
            is_required = prop_name in required
            req_marker = " [REQUIRED]" if is_required else " [optional]"
            prop_type = prop_info.get('type', 'string')
            prop_desc = prop_info.get('description', '')
            
            # Special handling for enum fields
            if 'enum' in prop_info:
                enum_values = ', '.join(f'"{v}"' for v in prop_info['enum'])
                params.append(f"  - {prop_name}{req_marker}: {prop_type} ({enum_values}) - {prop_desc}")
            else:
                params.append(f"  - {prop_name}{req_marker}: {prop_type} - {prop_desc}")
        
        tool_desc = f"- {tool['name']}: {tool['description']}"
        if params:
            tool_desc += "\n" + "\n".join(params)
        
        tool_descriptions.append(tool_desc)
    
    tools_text = "\n\n".join(tool_descriptions)
    
    return f"""Analyze this user input and create a structured plan:

User Input: "{user_input}"
Chat ID: {chat_id}
User ID: {user_id}

Available Tools:
{tools_text}

INTENT CLASSIFICATION EXAMPLES:

1. LIST MANAGEMENT (list.add, list.remove, list.create):
   - "Add milk to the shopping list" → intent: "list.add"
   - "Añade mantequilla a la lista de la compra" → intent: "list.add"
   - "Por favor, añade pan a la lista" → intent: "list.add"
   - "Remove eggs from grocery list" → intent: "list.remove"
   - "Create a list for vacation planning" → intent: "list.create"
   - "Delete the shopping list" → intent: "list.delete"
   - Keywords: "add to list", "añade a la lista", "a la lista de", "remove from list", "create list"
   - CRITICAL: If the phrase contains "a la lista" or "to the list" or "to list" → ALWAYS use list.* intent

2. TASK MANAGEMENT (task.create, task.complete, task.update):
   - "Remind me to call John tomorrow" → intent: "task.create"
   - "I need to finish the report by Friday" → intent: "task.create"
   - "Mark the laundry task as done" → intent: "task.complete"
   - "Change the deadline for project X" → intent: "task.update"
   - Keywords: "remind me", "I need to", "finish by", "mark as done", "deadline"
   - NOTE: If it mentions "lista" or "list" explicitly → it's list.*, NOT task.*

3. NOTE TAKING (memory.note):
   - "Remember that John likes coffee" → intent: "memory.note"
   - "Note: the meeting went well" → intent: "memory.note"
   - "Sarah's birthday is June 15th" → intent: "memory.note"
   - Keywords: "remember", "note", general facts/information WITHOUT "list" mention

4. DIARY ENTRY (diary.entry):
   - "Today I had lunch with Maria" → intent: "diary.entry"
   - "Went to the gym this morning" → intent: "diary.entry"
   - Keywords: "today I", "this morning", personal journal-style

5. QUERY (command.query):
   - "What's on my shopping list?" → intent: "command.query"
   - "When is my dentist appointment?" → intent: "command.query"
   - Keywords: questions about stored information

Create a JSON plan with this EXACT structure:
{{
    "intent": "memory.note",
    "entities": {{
        "people": ["name1", "name2"],
        "places": ["location1"],
        "dates": ["2025-10-20"],
        "tags": ["tag1"]
    }},
    "followups": [
        {{"ask": "What is...?", "field": "due_date"}}
    ],
    "actions": [
        {{"tool": "task_tool", "params": {{"operation": "create_task", "title": "...", "due_at": "..."}}}}
    ],
    "safety": {{"blocked": false, "reason": null}},
    "confidence": 0.9,
    "reasoning": "User wants to..."
}}

CRITICAL RULES:
1. "intent" MUST be ONE value from: task.create, task.complete, task.update, task.delete, list.create, list.delete, list.add, list.remove, list.item.complete, reminder.schedule, reminder.cancel, memory.note, diary.entry, command.query, unknown
2. NEVER use pipe "|" or combine multiple intents - choose the PRIMARY intent only
3. INTENT PRIORITY - KEYWORD DETECTION (HIGHEST PRIORITY):
   - If input contains "a la lista" OR "to the list" OR "to list" OR "from list" → MUST be list.* (list.add, list.remove, etc), NEVER task.* or memory.*
   - If input contains "añade" + "lista" OR "add" + "list" → MUST be list.add
   - If input contains "remind me" OR "I need to" (without "list") → MUST be task.create
   - "por favor" or "please" does NOT change the intent - ignore politeness words
4. Followup format: {{"ask": "question text", "field": "field_name"}} (use "ask" not "question")
5. Use ISO 8601 format for dates/times (YYYY-MM-DDTHH:MM:SS)
6. Include ALL required parameters for each tool (marked with [REQUIRED])
7. For task_tool: MUST include "operation" parameter (create_task, list_tasks, etc)
8. For memory_note_tool: MUST include both "title" and "content"
9. Only propose actions if you have enough information
10. Ask followup questions only for REQUIRED missing fields
11. Set confidence based on how clear the input is (0.0 to 1.0)
12. SAFETY: Set "blocked": false for ALL normal operations (notes, tasks, lists, reminders)
    - ONLY set "blocked": true for truly dangerous operations (delete all data, harmful content, etc)
    - Creating notes, tasks, reminders is SAFE - never block these!
    - "non-urgent" is NOT a reason to block - user wants to save the information"""


def plan_from_input(
    user_input: str, chat_id: str = "default", user_id: str = "user", llm=None
) -> Plan:
    """Generate a Plan from user input using LLM directly.

    Args:
        user_input: Raw user input
        chat_id: Chat identifier
        user_id: User identifier
        llm: Optional LLM configuration (unused, kept for compatibility)

    Returns:
        Validated Plan object
    """
    logger.debug("plan.start", extra={"user_input": user_input, "chat_id": chat_id})

    try:
        # Get LLM service
        llm_service = get_llm_service()
        
        # Build planning prompt
        prompt = _build_planning_prompt(user_input, chat_id, user_id)
        
        # Get LLM to generate plan
        system_prompt = """You are a planning assistant that analyzes user input and creates structured plans.
You output ONLY valid JSON, never any explanation or markdown formatting.
Be precise, concise, and always follow the exact JSON structure requested.

CRITICAL KEYWORD-BASED INTENT DETECTION (HIGHEST PRIORITY): 
- If input contains "a la lista" OR "to the list" OR "to list" → ALWAYS use list.* intent (list.add, list.remove, etc)
- If input contains "añade" + "lista" OR "add" + "list" → ALWAYS use list.add intent
- IGNORE politeness words like "por favor", "please", "could you" when detecting intent
- The "intent" field must be EXACTLY ONE value (like "memory.note"), never combine with "|"
- The "followups" field must use "ask" not "question"
- SAFETY: Always set "blocked": false for normal operations (notes, tasks, lists, reminders)
  - NEVER block memory notes, tasks, or reminders - these are safe operations the user wants!
  - ONLY block truly dangerous operations (delete all data, harmful content, system commands)
- All enum values must match exactly as specified in the prompt"""
        
        plan_data = llm_service.generate_json(prompt, system_prompt)
        
        # Validate and create Plan object
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
        print(f"      ⚠️  Planning error: {type(e).__name__}: {str(e)}")
        logger.error("plan.parse_failed", extra={"error": str(e), "error_type": type(e).__name__, "user_input": user_input[:100]})
        # Return a fallback plan for memory notes (most common case)
        # Extract a simple title from the user input (first 50 chars or first sentence)
        title = user_input[:50] + "..." if len(user_input) > 50 else user_input
        if "." in title:
            title = title.split(".")[0]
        
        return Plan(
            intent="memory.note",
            reasoning=f"Fallback plan due to error: {str(e)}",
            confidence=0.3,
            actions=[{
                "tool": "memory_note_tool",
                "params": {
                    "title": title,
                    "content": user_input,
                    "tags": []
                }
            }]
        )
