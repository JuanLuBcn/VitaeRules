"""Task Searcher Agent for UnifiedSearchCrew.

The TaskSearcher searches tasks and reminders based on search criteria.
"""

from crewai import Agent

from app.tools.task_search_tool import TaskSearchTool


def create_task_searcher_agent(llm=None, task_search_tool=None) -> Agent:
    """Create the Task Searcher Agent.

    Args:
        llm: Optional LLM configuration. If None, uses CrewAI defaults.
        task_search_tool: Task search tool instance (default: create new)

    Returns:
        CrewAI Agent configured for task search.
    """
    # Create tool if not provided
    if task_search_tool is None:
        task_search_tool = TaskSearchTool()
    
    agent_config = {
        "role": "Task Searcher",
        "goal": (
            "Search tasks and reminders to find items matching the user's query, "
            "considering status, due dates, priorities, and content"
        ),
        "backstory": (
            "You are an expert at task management and retrieval. You understand how "
            "to filter tasks by status (pending, completed), priority (urgent vs normal), "
            "due dates (overdue, upcoming, today), and content matching. You know users "
            "often search for 'what do I need to do', 'tasks for today', 'overdue items', "
            "or specific task titles. You retrieve tasks with all relevant metadata "
            "(title, due date, priority, status, description) and present them in a "
            "useful format.\n\n"
            "CRITICAL FORMAT RULES:\n"
            "1. Output ONLY ONE tool call at a time\n"
            "2. NEVER output both Action and Final Answer together\n"
            "3. Use ONLY dictionary format: {\"key\": \"value\"}\n"
            "4. NEVER use array format: [{...}, {...}]\n"
            "5. Example CORRECT format:\n"
            "   Action: task_search\n"
            "   Action Input: {\"completed\": null, \"search_query\": \"meeting\"}\n"
            "6. Example INCORRECT (DO NOT USE):\n"
            "   [{\"completed\": null}, {\"tasks\": []}]\n\n"
            "If you get 'Action Input is not a valid key, value dictionary' error:\n"
            "- You are outputting an array instead of a dict\n"
            "- Or you are trying to predict the tool's output\n"
            "- Only provide the INPUT to the tool, never the expected OUTPUT"
        ),
        "verbose": True,
        "allow_delegation": False,
        "tools": [task_search_tool],
        "max_iter": 5,
    }

    if llm:
        agent_config["llm"] = llm

    return Agent(**agent_config)
