"""Unified Search Crew - Searches across memory, tasks, and lists.

The Unified Search Crew coordinates searches across multiple data sources,
combining results intelligently based on query intent.
"""

import os
from dataclasses import dataclass

from crewai import Crew, Process

from app.config import get_settings
from app.crews.search.aggregator import create_result_aggregator_agent
from app.crews.search.coordinator import create_search_coordinator_agent
from app.crews.search.list_searcher import create_list_searcher_agent
from app.crews.search.memory_searcher import create_memory_searcher_agent
from app.crews.search.task_searcher import create_task_searcher_agent
from app.llm.crewai_llm import get_crewai_llm
from app.memory.api import MemoryService
from app.tools.list_tool import ListTool
from app.tools.task_tool import TaskTool
from app.tracing import get_tracer
from app.crews.search.models import SearchStrategy

logger = get_tracer()


@dataclass
class SearchContext:
    """Context for a search operation."""

    chat_id: str
    user_id: str
    sources: list[str] = None  # None = search all sources


@dataclass
class SearchResult:
    """Result of a unified search operation."""

    query: str
    sources_searched: list[str]
    memory_results: list[dict]
    task_results: list[dict]
    list_results: list[dict]
    combined_summary: str
    total_results: int


class UnifiedSearchCrew:
    """Unified Search Crew orchestrator.

    Manages the full search workflow:
    1. Coordination: Analyze query → determine sources to search
    2. Parallel Search: Search memory, tasks, lists (as needed)
    3. Aggregation: Combine and rank results
    """

    def __init__(
        self,
        memory_service: MemoryService | None = None,
        task_tool: TaskTool | None = None,
        list_tool: ListTool | None = None,
        llm=None,
    ):
        """Initialize the Unified Search Crew.

        Args:
            memory_service: Memory service for searching memories
            task_tool: Task tool for searching tasks
            list_tool: List tool for searching lists
            llm: Optional LLM configuration
        """
        self.memory_service = memory_service or MemoryService()
        self.task_tool = task_tool or TaskTool()
        self.list_tool = list_tool or ListTool()
        self.llm = llm

        # CrewAI components (lazy initialization)
        self._agents_initialized = False
        self.coordinator_agent = None
        self.memory_searcher_agent = None
        self.task_searcher_agent = None
        self.list_searcher_agent = None
        self.aggregator_agent = None
        self._crew = None

    def _initialize_agents(self):
        """Lazy initialization of CrewAI agents with shared memory.

        This is called on first use to avoid initialization overhead
        until actually needed.
        """
        if self._agents_initialized:
            return

        logger.info("Initializing CrewAI agents for UnifiedSearchCrew")

        # Get CrewAI-compatible LLM
        crewai_llm = get_crewai_llm(self.llm)
        logger.info("CrewAI LLM obtained successfully")

        # Create search tools
        from app.tools.memory_search_tool import MemorySearchTool
        from app.tools.task_search_tool import TaskSearchTool
        from app.tools.list_search_tool import ListSearchTool
        
        memory_search_tool = MemorySearchTool(self.memory_service)
        task_search_tool = TaskSearchTool(self.task_tool)
        list_search_tool = ListSearchTool(self.list_tool)

        # Create agents with CrewAI LLM and tools
        self.coordinator_agent = create_search_coordinator_agent(crewai_llm)
        self.memory_searcher_agent = create_memory_searcher_agent(crewai_llm, memory_search_tool)
        self.task_searcher_agent = create_task_searcher_agent(crewai_llm, task_search_tool)
        self.list_searcher_agent = create_list_searcher_agent(crewai_llm, list_search_tool)
        self.aggregator_agent = create_result_aggregator_agent(crewai_llm)
        logger.info("CrewAI agents created successfully")

        # Configure Ollama embeddings for CrewAI memory (use Ollama instead of OpenAI)
        settings = get_settings()
        os.environ["EMBEDDINGS_OLLAMA_MODEL_NAME"] = "nomic-embed-text"
        os.environ["EMBEDDINGS_OLLAMA_BASE_URL"] = settings.ollama_base_url

        embedder_config = {
            "provider": "ollama",
            "config": {"model": "nomic-embed-text"},
        }

        # Create CrewAI Crew with shared memory and custom embeddings
        self._crew = Crew(
            agents=[
                self.coordinator_agent,
                self.memory_searcher_agent,
                self.task_searcher_agent,
                self.list_searcher_agent,
                self.aggregator_agent,
            ],
            memory=settings.crewai_enable_memory,
            embedder=embedder_config,
            process=Process.sequential,
            verbose=True,
            full_output=True,
        )

        logger.info("CrewAI crew initialized successfully")
        self._agents_initialized = True

    async def search_with_crew_tasks(
        self,
        query: str,
        context: SearchContext,
    ) -> SearchResult:
        """Execute unified search using CrewAI orchestration with shared memory.

        This method uses CrewAI's task-based workflow where agents collaborate:
        1. Coordinator analyzes query → determines sources to search
        2. Searchers execute searches (memory, tasks, lists) → return results
        3. Aggregator combines results → produces unified response

        Args:
            query: Search query from user
            context: Search context with chat/user IDs and source preferences

        Returns:
            SearchResult with results from all searched sources
        """
        from crewai import Task

        # Initialize agents if not already done
        self._initialize_agents()
        
        # Update tool contexts with current user/chat IDs
        from app.tools.memory_search_tool import MemorySearchTool
        from app.tools.task_search_tool import TaskSearchTool
        from app.tools.list_search_tool import ListSearchTool
        
        MemorySearchTool._user_id = context.user_id
        MemorySearchTool._chat_id = context.chat_id
        TaskSearchTool._user_id = context.user_id
        TaskSearchTool._chat_id = context.chat_id
        ListSearchTool._user_id = context.user_id
        ListSearchTool._chat_id = context.chat_id

        logger.info("Starting crew.kickoff() for unified search")

        # Determine which sources to search
        sources = context.sources or ["memory", "tasks", "lists"]
        sources_str = ", ".join(sources)

        # Task 1: Coordination - analyze query and determine search strategy
        coordination_task = Task(
            description=f"""Analyze this search query and determine the best search strategy:

Query: "{query}"
Available sources: {sources_str}

Determine:
1. Which sources are most relevant to this query?
   - Memory: for notes, diary entries, stored information
   - Tasks: for todos, reminders, scheduled items
   - Lists: for list items, shopping lists, collections
2. What are the key search terms and entities?
   - People mentioned
   - Dates/times referenced
   - Topics or keywords
3. How should results be prioritized?

Output a search strategy with recommended sources and search criteria.""",
            agent=self.coordinator_agent,
            expected_output="Search strategy with recommended sources and criteria",
            output_pydantic=SearchStrategy,
        )

        # Task 2: Memory Search (if applicable)
        memory_search_task = Task(
            description=f"""Search long-term memory based on the coordinator's strategy.

Query: "{query}"

⚠️ MANDATORY: YOU MUST CALL THE memory_search TOOL - DO NOT ANSWER WITHOUT CALLING IT ⚠️

INSTRUCTIONS:
1. FIRST: Call the memory_search tool with a comprehensive semantic query
2. WAIT for the tool to return actual database results
3. ONLY report what the tool actually returned - copy the exact content, timestamps, and metadata
4. DO NOT invent or assume entities, people, places, or items that weren't explicitly mentioned in the original query or coordinator's analysis
5. If no results are found, report "No memories found matching the query" - do NOT fabricate or hallucinate results
6. Return ONLY the actual memories retrieved from the database, with their metadata (timestamps, people, locations, tags)
7. Use the coordinator's recommended filters (people, dates, tags, location) ONLY if they were explicitly mentioned

🚫 FORBIDDEN:
- Generating answers without calling the tool
- Making up timestamps (especially dates from 2023 when the app was created in 2025)
- Inventing names, places, or content that wasn't in the tool's response
- Assuming what might be in the database

IMPORTANT: Semantic search handles multiple concepts in one query. You do NOT need to perform multiple separate searches.""",
            agent=self.memory_searcher_agent,
            context=[coordination_task],
            expected_output="List of relevant memories with metadata, or 'No memories found'",
        )

        # Task 3: Task Search (if applicable)
        task_search_task = Task(
            description=f"""Search tasks and reminders based on the coordinator's strategy.

Query: "{query}"

INSTRUCTIONS:
1. Use the task_tool ONCE to search for relevant tasks
2. Filter by status, due date, and priority as recommended by the coordinator
3. DO NOT invent tasks or assume what tasks might exist
4. If no results are found, report "No tasks found matching the query"
5. Return ONLY actual tasks from the database with their metadata (title, due date, priority, status, description)

Focus on the query's actual intent - search for what was asked, not what you think might exist.""",
            agent=self.task_searcher_agent,
            context=[coordination_task],
            expected_output="List of relevant tasks with metadata, or 'No tasks found'",
        )

        # Task 4: List Search (if applicable)
        list_search_task = Task(
            description=f"""Search lists and list items based on the coordinator's strategy.

Query: "{query}"

INSTRUCTIONS:
1. Use the list_tool ONCE to search for relevant lists and items
2. Search list names and item contents as recommended by the coordinator
3. DO NOT invent lists or items that don't exist
4. If no results are found, report "No lists found matching the query"
5. Return ONLY actual lists and items from the database with their metadata (list name, position, status, tags, location)

Focus on the query's actual intent - search for what was asked, not what you think might exist.""",
            agent=self.list_searcher_agent,
            context=[coordination_task],
            expected_output="List of relevant list items grouped by list, or 'No lists found'",
        )

        # Task 5: Aggregation - combine and format results
        aggregation_task = Task(
            description=f"""Combine search results from all sources into a unified response:

Original query: "{query}"

Using results from previous tasks:

IF RESULTS WERE FOUND (memories, tasks, or lists):
1. Deduplicate similar results across sources
2. Rank all results by relevance to the original query
3. Format into a clear, user-friendly response
4. Provide:
   - Summary of what was found (counts by source type)
   - Top results from each source with context
   - Overall relevance score or recommendation

IF NO RESULTS WERE FOUND in any source:
1. You MUST respond with EXACTLY: "I don't have that information. Can you provide more details?"
2. DO NOT use general knowledge to answer the question
3. DO NOT make up or invent any information
4. DO NOT guess or estimate values
5. ONLY return information that was actually found in the search results

CRITICAL: If searches returned empty results, you MUST say "I don't have that information."
Never fabricate answers even if the question seems like common knowledge.

Make the response concise but informative.""",
            agent=self.aggregator_agent,
            context=[
                coordination_task,
                memory_search_task,
                task_search_task,
                list_search_task,
            ],
            expected_output="Unified search results summary with all findings, or general knowledge answer, or request for clarification",
        )

        # Execute coordinator first to determine which sources to search
        logger.info("Executing coordinator to analyze query")
        coordination_task_for_execution = Task(
            description=coordination_task.description,
            agent=self.coordinator_agent,
            expected_output=coordination_task.expected_output,
            output_pydantic=SearchStrategy,
        )
        
        # Temporarily set crew tasks to just coordinator
        self._crew.tasks = [coordination_task_for_execution]
        
        coordinator_result = self._crew.kickoff(
            inputs={
                "query": query,
                "sources": sources_str,
                "chat_id": context.chat_id,
                "user_id": context.user_id,
            }
        )
        
        # Parse coordinator output (Pydantic model)
        search_strategy = coordinator_result.pydantic
        logger.info(f"Coordinator strategy: {search_strategy}")
        
        # Determine which searches to execute based on structured output
        should_search_memory = search_strategy.memory.relevant
        should_search_tasks = search_strategy.tasks.relevant
        should_search_lists = search_strategy.lists.relevant
        
        logger.info(f"Search decisions - Memory: {should_search_memory}, Tasks: {should_search_tasks}, Lists: {should_search_lists}")
        
        # Build task list conditionally
        tasks_to_execute = [coordination_task]  # Always include coordination (already executed)
        search_tasks_context = [coordination_task]  # Context for aggregator
        
        if should_search_memory:
            logger.info("Adding memory search task (HIGH/MEDIUM relevance)")
            tasks_to_execute.append(memory_search_task)
            search_tasks_context.append(memory_search_task)
        else:
            logger.info("Skipping memory search (LOW relevance)")
        
        if should_search_tasks:
            logger.info("Adding task search task (HIGH/MEDIUM relevance)")
            tasks_to_execute.append(task_search_task)
            search_tasks_context.append(task_search_task)
        else:
            logger.info("Skipping task search (LOW relevance)")
        
        if should_search_lists:
            logger.info("Adding list search task (HIGH/MEDIUM relevance)")
            tasks_to_execute.append(list_search_task)
            search_tasks_context.append(list_search_task)
        else:
            logger.info("Skipping list search (LOW relevance)")
        
        # Update aggregation task context to only include executed searches
        aggregation_task.context = search_tasks_context
        tasks_to_execute.append(aggregation_task)
        
        logger.info(f"Executing {len(tasks_to_execute)} tasks total ({len(search_tasks_context) - 1} searches)")
        
        # Set tasks on the crew
        self._crew.tasks = tasks_to_execute

        # Execute the remaining crew workflow
        try:
            result = self._crew.kickoff(
                inputs={
                    "query": query,
                    "sources": sources_str,
                    "chat_id": context.chat_id,
                    "user_id": context.user_id,
                }
            )

            logger.info("Crew.kickoff() completed successfully for search")

            # Parse final answer from CrewOutput
            final_answer = result.raw if hasattr(result, "raw") else str(result)

            # For now, return a structured result with the crew output
            # In a full implementation, we'd parse the task outputs to extract actual data
            return SearchResult(
                query=query,
                sources_searched=sources,
                memory_results=[],  # Would parse from memory_search_task output
                task_results=[],  # Would parse from task_search_task output
                list_results=[],  # Would parse from list_search_task output
                combined_summary=final_answer,
                total_results=0,  # Would count from parsed results
            )

        except Exception as e:
            logger.error(
                "CrewAI kickoff failed for search",
                extra={"error": str(e), "query": query},
            )
            raise
