"""
QueryPlanner agent for Retrieval Crew.

Analyzes user questions and produces structured Query contracts.
"""

from crewai import Agent, Task

from app.contracts.query import Query, QueryFilters, QueryIntent
from app.tracing import get_tracer

logger = get_tracer()


def create_query_planner_agent(llm) -> Agent:
    """
    Create the QueryPlanner agent.

    Analyzes user questions to:
    - Classify intent (factual, temporal, list, summary)
    - Extract filters (people, places, dates, tags)
    - Determine appropriate search scope
    """
    return Agent(
        role="Query Planner",
        goal="Analyze user questions and produce structured queries for memory search",
        backstory="""You are an expert at understanding user questions and translating 
        them into structured search queries. You identify the intent (factual, temporal, 
        list, or summary), extract relevant filters (people, places, dates, tags), and 
        determine the appropriate search scope.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def create_query_planning_task(
    agent: Agent, user_question: str, chat_id: str, user_id: str
) -> Task:
    """Create task for analyzing and structuring the user's question."""
    return Task(
        description=f"""
        Analyze this user question and produce a structured Query:
        
        Question: "{user_question}"
        
        Classify the intent:
        - FACTUAL: What, who, where questions about facts
        - TEMPORAL: When, time-based questions (yesterday, last week, etc.)
        - LIST: List all X, show me all Y
        - SUMMARY: Summarize, give overview, what happened
        
        Extract filters from the question:
        - people: Names of people mentioned
        - places: Locations mentioned
        - tags: Topics or categories
        - date_range: Time constraints (start/end dates)
        - sections: diary, task, note, reminder (if specific type requested)
        
        Determine max_results (default 10, more for list queries).
        
        Return a JSON Query object with all extracted information.
        """,
        agent=agent,
        expected_output="A JSON Query object with intent, filters, and reasoning",
    )


def plan_query_from_question(
    user_question: str, chat_id: str, user_id: str, llm
) -> Query:
    """
    Analyze a user question and produce a structured Query.

    Args:
        user_question: The user's natural language question
        chat_id: Chat context identifier
        user_id: User identifier
        llm: Language model for the agent

    Returns:
        Query object with intent classification and extracted filters
    """
    try:
        agent = create_query_planner_agent(llm)
        task = create_query_planning_task(agent, user_question, chat_id, user_id)

        # TODO: Actually execute the CrewAI task and parse result to Query
        # For now, return a basic query with keyword-based intent detection
        logger.warning(
            "QueryPlanner not yet integrated with LLM, using keyword fallback"
        )

        query_lower = user_question.lower()
        intent = QueryIntent.UNKNOWN

        if any(word in query_lower for word in ["what did", "what happened", "summary"]):
            if "list" in query_lower or "all" in query_lower:
                intent = QueryIntent.LIST
            elif "when" in query_lower:
                intent = QueryIntent.TEMPORAL
            elif "summary" in query_lower or "summarize" in query_lower:
                intent = QueryIntent.SUMMARY
            else:
                intent = QueryIntent.FACTUAL
        elif any(word in query_lower for word in ["when", "yesterday", "last week", "today"]):
            intent = QueryIntent.TEMPORAL
        elif any(word in query_lower for word in ["list all", "show me all", "what are"]):
            intent = QueryIntent.LIST

        return Query(
            query_text=user_question,
            intent=intent,
            filters=QueryFilters(),
            max_results=20 if intent == QueryIntent.LIST else 10,
            reasoning=f"Keyword-based classification: detected '{intent.value}' intent",
        )

    except Exception as e:
        logger.error(f"Query planning failed: {e}")
        return Query(
            query_text=user_question,
            intent=QueryIntent.UNKNOWN,
            filters=QueryFilters(),
            reasoning=f"Error during planning: {str(e)}",
        )
