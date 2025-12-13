"""Memory Searcher Agent for UnifiedSearchCrew.

The MemorySearcher searches long-term memory (notes, diary entries, memories)
based on search criteria from the coordinator.
"""

from crewai import Agent

from app.tools.memory_search_tool import MemorySearchTool


def create_memory_searcher_agent(llm=None, memory_search_tool=None) -> Agent:
    """Create the Memory Searcher Agent.

    Args:
        llm: Optional LLM configuration. If None, uses CrewAI defaults.
        memory_search_tool: Memory search tool instance (default: create new)

    Returns:
        CrewAI Agent configured for memory search.
    """
    # Create tool if not provided
    if memory_search_tool is None:
        memory_search_tool = MemorySearchTool()
    
    agent_config = {
        "role": "Memory Searcher",
        "goal": (
            "Search long-term memory for relevant notes, diary entries, and "
            "stored information matching the user's query"
        ),
        "backstory": (
            "You are a specialist in semantic memory search. You MUST ALWAYS use the memory_search tool - "
            "NEVER generate answers from your own knowledge. You understand how to "
            "query the long-term memory database effectively using semantic similarity. "
            "You retrieve memories with their metadata (timestamps, people, locations, tags) "
            "and rank them by relevance. You are honest and precise - you ONLY return "
            "what is actually found in the database. If no memories match the query, "
            "you clearly state 'No memories found' rather than inventing or assuming results. "
            "You use ONE comprehensive semantic query rather than multiple keyword searches. \n\n"
            "CRITICAL RULES:\n"
            "1. ALWAYS call the memory_search tool - do NOT answer without calling it\n"
            "2. NEVER make up timestamps, names, or content that wasn't returned by the tool\n"
            "3. If the tool returns no results, say 'No memories found' - do NOT fabricate results\n"
            "4. Only report what the tool actually returned - nothing more, nothing less"
        ),
        "verbose": True,
        "allow_delegation": False,
        "tools": [memory_search_tool],
    }

    if llm:
        agent_config["llm"] = llm

    return Agent(**agent_config)
