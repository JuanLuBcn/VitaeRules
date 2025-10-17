"""
Retriever agent for Retrieval Crew.

Searches long-term memory using Query filters and returns relevant MemoryItems.
"""

from crewai import Agent, Task

from app.contracts.query import Query
from app.memory import MemoryItem, MemoryQuery, MemoryService
from app.tracing import get_tracer

logger = get_tracer()


def create_retriever_agent(llm) -> Agent:
    """
    Create the Retriever agent.

    Searches long-term memory using:
    - Vector similarity for semantic search
    - SQL filters for structured constraints (people, places, dates, sections)
    - Relevance scoring and ranking
    """
    return Agent(
        role="Memory Retriever",
        goal="Search long-term memory and return relevant items matching the query",
        backstory="""You are an expert at searching through structured memory stores. 
        You use both semantic similarity (vector search) and structured filters (SQL) 
        to find the most relevant memories. You rank results by relevance and return 
        only the most pertinent items.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def create_retrieval_task(
    agent: Agent, query: Query, chat_id: str, user_id: str
) -> Task:
    """Create task for searching memory based on Query."""
    return Task(
        description=f"""
        Search long-term memory for items matching this query:
        
        Query: "{query.query_text}"
        Intent: {query.intent.value}
        Filters: {query.filters.model_dump() if query.filters else "None"}
        Max Results: {query.max_results}
        
        Use vector similarity search for semantic matching.
        Apply SQL filters for:
        - people: {query.filters.people if query.filters else []}
        - places: {query.filters.places if query.filters else []}
        - date_range: {query.filters.date_range if query.filters else None}
        - sections: {query.filters.sections if query.filters else []}
        - tags: {query.filters.tags if query.filters else []}
        
        Return the top {query.max_results} most relevant MemoryItems with relevance scores.
        """,
        agent=agent,
        expected_output=f"List of up to {query.max_results} MemoryItems ranked by relevance",
    )


def retrieve_memories(
    query: Query, chat_id: str, user_id: str, memory_service: MemoryService, llm
) -> list[MemoryItem]:
    """
    Search long-term memory and return relevant items.

    Args:
        query: Structured query with intent and filters
        chat_id: Chat context identifier
        user_id: User identifier
        memory_service: Memory service for LTM access
        llm: Language model for the agent

    Returns:
        List of MemoryItems matching the query, ranked by relevance
    """
    try:
        agent = create_retriever_agent(llm)
        task = create_retrieval_task(agent, query, chat_id, user_id)

        # TODO: Actually execute CrewAI task with LTM vector search
        # For now, use basic memory service search
        logger.info(f"Retrieving memories for query: {query.query_text}")

        # Build MemoryQuery from Query
        memory_query = MemoryQuery(
            query=query.query_text,
            top_k=query.max_results,
            people=query.filters.people if query.filters else None,
            tags=query.filters.tags if query.filters else None,
            start_date=query.filters.date_range.start if query.filters and query.filters.date_range else None,
            end_date=query.filters.date_range.end if query.filters and query.filters.date_range else None,
        )

        # Search LTM
        search_results = memory_service.ltm.search(memory_query)

        # Extract MemoryItems from search results
        results = [sr.item for sr in search_results]

        logger.info(f"Found {len(results)} memories matching query")
        return results

    except Exception as e:
        logger.error(f"Memory retrieval failed: {e}")
        return []
