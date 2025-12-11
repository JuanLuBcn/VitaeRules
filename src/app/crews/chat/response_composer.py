"""Response Composer Agent for ChatCrew.

The ResponseComposer creates final responses by combining conversation context,
search results, or action outcomes into natural, user-friendly messages.
"""

from crewai import Agent


def create_response_composer_agent(llm=None) -> Agent:
    """Create the Response Composer Agent.

    Args:
        llm: Optional LLM configuration. If None, uses CrewAI defaults.

    Returns:
        CrewAI Agent configured for response composition.
    """
    agent_config = {
        "role": "Response Composer",
        "goal": (
            "Compose natural, helpful responses by integrating conversation context, "
            "search results, and action outcomes"
        ),
        "backstory": (
            "You are a master at crafting natural, friendly responses. You take "
            "information from various sources (search results, action confirmations, "
            "conversation history) and weave them into coherent, helpful messages. "
            "When presenting search results, you integrate them naturally with proper "
            "context ('Based on what I found...', 'According to your notes...'). "
            "When confirming actions, you're clear about what was done ('I've created "
            "a reminder to...', 'I've added X to your list'). You maintain the "
            "conversation tone - warm for casual chat, informative for searches, "
            "confirmatory for actions. You never overwhelm users with too much "
            "information at once - you summarize and offer to provide more details "
            "if needed."
        ),
        "verbose": True,
        "allow_delegation": False,
    }

    if llm:
        agent_config["llm"] = llm

    return Agent(**agent_config)
