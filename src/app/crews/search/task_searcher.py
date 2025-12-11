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
            "useful format."
        ),
        "verbose": True,
        "allow_delegation": False,
        "tools": [task_search_tool],
    }

    if llm:
        agent_config["llm"] = llm

    return Agent(**agent_config)
