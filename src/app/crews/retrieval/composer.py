"""
Composer agent for Retrieval Crew.

Generates grounded answers with citations from retrieved memories.
Enforces zero-evidence policy.
"""

from datetime import datetime

from crewai import Agent, Task

from app.contracts.query import Citation, GroundedAnswer, Query
from app.memory import MemoryItem
from app.tracing import get_tracer

logger = get_tracer()


def create_composer_agent(llm) -> Agent:
    """
    Create the Composer agent.

    Generates answers that:
    - Are strictly grounded in retrieved memories
    - Include inline citations [1], [2], etc.
    - Explicitly state when evidence is insufficient
    - Follow zero-evidence policy (no unsourced claims)
    """
    return Agent(
        role="Answer Composer",
        goal="Generate grounded answers with citations from retrieved memories",
        backstory="""You are an expert at synthesizing information from multiple sources 
        and presenting it clearly with proper citations. You NEVER make claims without 
        evidence. If the retrieved memories don't contain the answer, you explicitly 
        state that. You use inline citations [1], [2] to reference sources.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )


def create_composition_task(
    agent: Agent, query: Query, memories: list[MemoryItem], chat_id: str, user_id: str
) -> Task:
    """Create task for composing a grounded answer."""
    memory_summary = "\n\n".join(
        [
            f"[{i+1}] {m.title or 'Untitled'} ({m.created_at})\n{m.content[:500]}"
            for i, m in enumerate(memories)
        ]
    )

    return Task(
        description=f"""
        Compose a grounded answer to this question using ONLY the retrieved memories:
        
        Question: "{query.query_text}"
        
        Retrieved Memories ({len(memories)} items):
        {memory_summary if memory_summary else "No memories found."}
        
        Rules:
        1. ONLY use information from the retrieved memories above
        2. Include inline citations [1], [2], etc. for every claim
        3. If memories don't contain the answer, say "I don't have enough information to answer that"
        4. Do not infer or extrapolate beyond what's in the memories
        5. If partially answered, clearly state what's known vs unknown
        
        Provide:
        - A natural language answer with citations
        - Confidence score (0.0-1.0)
        - Explanation of how you composed the answer
        """,
        agent=agent,
        expected_output="A GroundedAnswer with answer text, citations, confidence, and has_evidence flag",
    )


def compose_answer(
    query: Query, memories: list[MemoryItem], chat_id: str, user_id: str, llm
) -> GroundedAnswer:
    """
    Compose a grounded answer from retrieved memories.

    Args:
        query: The user's structured query
        memories: Retrieved memory items
        chat_id: Chat context identifier
        user_id: User identifier
        llm: Language model for the agent

    Returns:
        GroundedAnswer with citations and zero-evidence enforcement
    """
    try:
        agent = create_composer_agent(llm)
        task = create_composition_task(agent, query, memories, chat_id, user_id)

        # TODO: Actually execute CrewAI task to compose answer with LLM
        # For now, provide basic composition logic
        logger.info(
            f"Composing answer for '{query.query_text}' from {len(memories)} memories"
        )

        if not memories:
            return GroundedAnswer(
                query=query.query_text,
                answer="I don't have any information in my memory to answer that question.",
                citations=[],
                confidence=0.0,
                has_evidence=False,
                reasoning="No memories found matching the query",
            )

        # Build citations
        citations = [
            Citation(
                memory_id=str(m.id),
                title=m.title,
                created_at=m.created_at,
                excerpt=m.content[:200] if m.content else None,
            )
            for m in memories[:5]  # Limit to top 5 citations
        ]

        # Compose basic answer
        answer_parts = []
        for i, memory in enumerate(memories[:3], 1):
            if memory.content:
                answer_parts.append(f"[{i}] {memory.content[:150]}...")

        answer = f"Based on my memory: {' '.join(answer_parts)}"

        return GroundedAnswer(
            query=query.query_text,
            answer=answer,
            citations=citations,
            confidence=0.7 if len(memories) >= 3 else 0.5,
            has_evidence=True,
            reasoning=f"Composed from {len(memories)} relevant memories",
        )

    except Exception as e:
        logger.error(f"Answer composition failed: {e}")
        return GroundedAnswer(
            query=query.query_text,
            answer=f"I encountered an error trying to answer your question: {str(e)}",
            citations=[],
            confidence=0.0,
            has_evidence=False,
            reasoning=f"Error during composition: {str(e)}",
        )
