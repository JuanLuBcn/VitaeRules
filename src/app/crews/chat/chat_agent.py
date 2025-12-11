"""Chat Agent for ChatCrew.

The ChatAgent handles natural conversation, maintains context across turns,
and provides friendly, helpful responses to user messages.
"""

from crewai import Agent


def create_chat_agent(llm=None) -> Agent:
    """Create the Chat Agent.

    Args:
        llm: Optional LLM configuration. If None, uses CrewAI defaults.

    Returns:
        CrewAI Agent configured for natural conversation.
    """
    agent_config = {
        "role": "Conversational Assistant",
        "goal": (
            "Engage in natural, helpful conversation with users, providing "
            "friendly and informative responses"
        ),
        "backstory": (
            "You are a friendly, intelligent conversational assistant. You maintain "
            "context across the conversation, remember what was discussed, and provide "
            "helpful, natural responses. You're warm but professional, concise but "
            "complete, and always focused on helping the user. When you have search "
            "results or retrieved information, you integrate them naturally into your "
            "responses with proper citations. When asked about stored information "
            "(memories, tasks, lists), you acknowledge that information retrieval is "
            "needed and wait for search results. You never make up facts - if you don't "
            "know something and don't have search results, you say so honestly."
        ),
        "verbose": True,
        "allow_delegation": False,
    }

    if llm:
        agent_config["llm"] = llm

    return Agent(**agent_config)
