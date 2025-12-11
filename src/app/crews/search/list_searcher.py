"""List Searcher Agent for UnifiedSearchCrew.

The ListSearcher searches lists and list items based on search criteria.
"""

from crewai import Agent

from app.tools.list_search_tool import ListSearchTool


def create_list_searcher_agent(llm=None, list_search_tool=None) -> Agent:
    """Create the List Searcher Agent.

    Args:
        llm: Optional LLM configuration. If None, uses CrewAI defaults.
        list_search_tool: List search tool instance (default: create new)

    Returns:
        CrewAI Agent configured for list search.
    """
    # Create tool if not provided
    if list_search_tool is None:
        list_search_tool = ListSearchTool()
    
    agent_config = {
        "role": "List Searcher",
        "goal": (
            "Search lists and list items to find matches for the user's query, "
            "considering list names, item text, completion status, and metadata"
        ),
        "backstory": (
            "You are a specialist in list management and search. You understand how "
            "users organize information in lists (shopping lists, todo lists, wish lists, "
            "reading lists, etc.). You can search both list names and item contents. "
            "You know how to filter by completion status (show pending items vs all items). "
            "You retrieve list items with context (which list they belong to, position, "
            "tags, location data if relevant). You present results grouped by list for "
            "clarity and usefulness."
        ),
        "verbose": True,
        "allow_delegation": False,
        "tools": [list_search_tool],
    }

    if llm:
        agent_config["llm"] = llm

    return Agent(**agent_config)
