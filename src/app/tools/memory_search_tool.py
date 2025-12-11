"""Memory Search Tool for searching long-term memories."""

from typing import Any, Optional

from crewai.tools import BaseTool as CrewAIBaseTool

from app.memory import MemoryQuery, MemoryService
from app.tracing import get_tracer


class MemorySearchTool(CrewAIBaseTool):
    """Tool for searching long-term memories using semantic similarity."""

    name: str = "memory_search"
    description: str = (
        "Search long-term memory for notes, diary entries, and stored information. "
        "Use this tool to find memories based on semantic similarity. "
        "Provide only the search query - user context is automatically included."
    )
    
    # Use class attributes to avoid Pydantic validation
    _memory_service: MemoryService | None = None
    _user_id: str = "default"
    _chat_id: str = "default"

    def __init__(
        self, 
        memory_service: MemoryService | None = None,
        user_id: str = "default",
        chat_id: str = "default"
    ):
        """Initialize Memory Search Tool.

        Args:
            memory_service: Memory service instance (default: create new)
            user_id: User identifier to store in context
            chat_id: Chat identifier to store in context
        """
        super().__init__()
        # Store in class attributes to avoid Pydantic validation
        MemorySearchTool._memory_service = memory_service or MemoryService()
        MemorySearchTool._user_id = user_id
        MemorySearchTool._chat_id = chat_id
        tracer = get_tracer()
        tracer.debug(f"MemorySearchTool initialized with user_id={user_id}, chat_id={chat_id}")

    def _run(
        self,
        query: str,
        limit: int = 5,
        people: Optional[str] = None,
        tags: Optional[str] = None,
        location: Optional[str] = None,
    ) -> str:
        """Search memories synchronously.

        Args:
            query: Search query text
            limit: Maximum number of results
            people: Comma-separated list of people to filter by
            tags: Comma-separated list of tags to filter by
            location: Location to filter by

        Returns:
            Formatted search results with metadata
        
        Note: user_id and chat_id are taken from the tool's stored context
        """
        try:
            # Build memory query - note: MemoryQuery doesn't have user_id/chat_id/limit
            # These are handled by the memory service internally
            memory_query = MemoryQuery(
                query=query,
                top_k=limit,
            )

            # Add filters if provided
            if people:
                memory_query.people = [p.strip() for p in people.split(",")]
            if tags:
                memory_query.tags = [t.strip() for t in tags.split(",")]

            # Execute search
            results = MemorySearchTool._memory_service.search_memories(memory_query)

            # Format results
            if not results:
                return "No memories found matching the query."

            formatted = []
            for i, result in enumerate(results, 1):
                memory = result.item  # MemorySearchResult has 'item', not 'memory'
                formatted.append(
                    f"\n{i}. **{memory.title}** (Relevance: {result.score:.2f})\n"
                    f"   Content: {memory.content}\n"
                    f"   Date: {memory.created_at}\n"
                    f"   People: {', '.join(memory.people) if memory.people else 'None'}\n"
                    f"   Tags: {', '.join(memory.tags) if memory.tags else 'None'}\n"
                    f"   Location: {memory.location or 'None'}"
                )

            return (
                f"Found {len(results)} memories:\n" + "\n".join(formatted)
            )

        except Exception as e:
            tracer = get_tracer()
            tracer.error(f"Memory search failed: {e}")
            return f"Memory search error: {str(e)}"
