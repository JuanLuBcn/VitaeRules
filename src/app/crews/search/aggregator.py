"""Result Aggregator Agent for UnifiedSearchCrew.

The ResultAggregator combines search results from multiple sources,
deduplicates, ranks by relevance, and formats the final response.
"""

from crewai import Agent


def create_result_aggregator_agent(llm=None) -> Agent:
    """Create the Result Aggregator Agent.

    Args:
        llm: Optional LLM configuration. If None, uses CrewAI defaults.

    Returns:
        CrewAI Agent configured for result aggregation.
    """
    agent_config = {
        "role": "Result Aggregator",
        "goal": (
            "Combine search results from multiple sources (memory, tasks, lists) "
            "into a unified, ranked, and well-formatted response"
        ),
        "backstory": (
            "You are an expert at information synthesis and presentation. You take "
            "results from different sources and merge them intelligently. You deduplicate "
            "similar items (e.g., a memory that mentions a task, and the actual task itself). "
            "You rank results by relevance to the original query, considering recency, "
            "importance, and semantic similarity. You format the final response in a "
            "user-friendly way, grouping by source type when helpful (e.g., 'Found 3 memories, "
            "2 tasks, and 1 list item'). You provide context for each result (dates, people, "
            "tags) to help users understand what they're seeing."
        ),
        "verbose": True,
        "allow_delegation": False,
    }

    if llm:
        agent_config["llm"] = llm

    return Agent(**agent_config)
