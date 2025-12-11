"""Search Coordinator Agent for UnifiedSearchCrew.

The SearchCoordinator analyzes search queries and determines which data sources
to search (memory, tasks, lists) and how to prioritize results.
"""

from crewai import Agent


def create_search_coordinator_agent(llm=None) -> Agent:
    """Create the Search Coordinator Agent.

    Args:
        llm: Optional LLM configuration. If None, uses CrewAI defaults.

    Returns:
        CrewAI Agent configured for search coordination.
    """
    agent_config = {
        "role": "Search Coordinator",
        "goal": (
            "Analyze search queries to determine which data sources to search "
            "(memory, tasks, lists) and how to combine results effectively"
        ),
        "backstory": (
            "You are an expert at understanding search intent and determining the "
            "best data sources to query. You analyze the semantic meaning of queries "
            "to identify if the user is looking for: memories/notes (use memory search), "
            "tasks/reminders (use task search), lists/items (use list search), or a "
            "combination. You understand the fundamental nature of what users want to "
            "find and recommend only searches that will provide value. You're strategic "
            "about which sources will yield the best results without unnecessary searches."
        ),
        "verbose": True,
        "allow_delegation": False,
    }

    if llm:
        agent_config["llm"] = llm

    return Agent(**agent_config)
