"""Intent Analyzer Agent for ChatCrew.

The IntentAnalyzer determines what the user wants to do: have a conversation,
search for information, or execute an action (create task, note, etc.).
"""

from crewai import Agent


def create_intent_analyzer_agent(llm=None) -> Agent:
    """Create the Intent Analyzer Agent.

    Args:
        llm: Optional LLM configuration. If None, uses CrewAI defaults.

    Returns:
        CrewAI Agent configured for intent analysis.
    """
    agent_config = {
        "role": "Intent Analyzer",
        "goal": (
            "Analyze user messages to determine their intent: "
            "information retrieval or action execution"
        ),
        "backstory": (
            "You are an expert at understanding the fundamental intent behind user messages. "
            "You analyze what users truly want to accomplish by examining the semantic meaning "
            "of their communication, not just surface-level patterns.\n\n"
            "You distinguish between two primary intents:\n\n"
            "**SEARCH**: The user seeks information they don't currently have. They are asking "
            "a question that requires retrieving data from memory, tasks, lists, or general knowledge. "
            "The core intent is to receive an answer.\n\n"
            "**ACTION**: The user wants to store information, execute a command, express themselves, "
            "or engage in communication. This includes providing new information, sharing experiences, "
            "giving instructions, or social interaction. The core intent is to communicate or record "
            "something, not to retrieve information.\n\n"
            "You focus on understanding what the user fundamentally wants to achieve, "
            "considering conversation context and the natural flow of dialogue. "
            "You default to ACTION when intent is ambiguous, ensuring valuable information isn't lost."
        ),
        "verbose": True,
        "allow_delegation": False,
    }

    if llm:
        agent_config["llm"] = llm

    return Agent(**agent_config)
