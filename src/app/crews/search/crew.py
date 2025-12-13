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

CRITICAL INSTRUCTIONS:
1. Call the task_search tool with a single dictionary input like: {{"search_query": "text", "completed": null}}
2. Use completed=null for all tasks, completed=false for pending, completed=true for completed
3. Extract search terms from the query (names, keywords, dates)
4. Wait for the tool result - DO NOT make up results
5. Return what the tool actually found

Example tool calls:
- {{"search_query": "birthday", "completed": null}}
- {{"completed": false}} (all pending tasks)
- {{"search_query": "Olivia", "completed": null}}

DO NOT return arrays like [{{"input": ...}}, {{"result": ...}}]. Call the tool properly and wait for results.""",
            agent=self.task_searcher_agent,
            context=[coordination_task],
            expected_output="Actual task search results from the tool, formatted clearly",
        )

        # Task 4: List Search (if applicable)
        list_search_task = Task(
            description=f"""Search lists and list items based on the coordinator's strategy.

Query: "{query}"

CRITICAL INSTRUCTIONS:
1. Call the list_search tool with a single dictionary input like: {{"search_query": "text"}}
2. Extract search terms from the query (names, keywords, categories)
3. Wait for the tool result - DO NOT make up results
4. Return what the tool actually found

Example tool calls:
- {{"search_query": "shopping"}}
- {{"search_query": "birthday"}}
- {{"search_query": "Olivia"}}

DO NOT return arrays like [{{"input": ...}}, {{"result": ...}}]. Call the tool properly and wait for results.""",
            agent=self.list_searcher_agent,
            context=[coordination_task],
            expected_output="Actual list search results from the tool, formatted clearly",
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
        
        # Helper function to determine if search should execute based on priority
        def should_execute_search(priority: str, has_high_priority_results: bool) -> bool:
            """
            Determine if a search should be executed based on its priority and previous results.
            
            Args:
                priority: Priority level (high, medium, low, very low)
                has_high_priority_results: Whether high priority searches already found results
            
            Returns:
                True if search should execute, False to skip
            """
            priority_lower = priority.lower()
            
            # Always execute HIGH and MEDIUM priority
            if priority_lower in ["high", "medium"]:
                return True
            
            # For LOW and VERY LOW, only execute if high priority found nothing
            if priority_lower in ["low", "very low"]:
                if has_high_priority_results:
                    logger.info(f"Skipping {priority} priority search - high priority search already found results")
                    return False
                return True
            
            # Default to executing
            return True
        
        # Phase 1: Execute HIGH priority searches first
        high_priority_tasks = []
        high_priority_found = False
        
        memory_priority = search_strategy.memory.priority.lower()
        tasks_priority = search_strategy.tasks.priority.lower()
        lists_priority = search_strategy.lists.priority.lower()
        
        logger.info(f"Search priorities - Memory: {memory_priority}, Tasks: {tasks_priority}, Lists: {lists_priority}")
        
        # Execute HIGH priority searches
        if search_strategy.memory.relevant and memory_priority == "high":
            logger.info("Executing HIGH priority: memory search")
            high_priority_tasks.append(memory_search_task)
        
        if search_strategy.tasks.relevant and tasks_priority == "high":
            logger.info("Executing HIGH priority: task search")
            high_priority_tasks.append(task_search_task)
        
        if search_strategy.lists.relevant and lists_priority == "high":
            logger.info("Executing HIGH priority: list search")
            high_priority_tasks.append(list_search_task)
        
        # If we have HIGH priority tasks, execute them first to check for results
        if high_priority_tasks:
            logger.info(f"Executing {len(high_priority_tasks)} HIGH priority searches first")
            self._crew.tasks = [coordination_task] + high_priority_tasks
            
            try:
                high_priority_result = self._crew.kickoff(
                    inputs={
                        "query": query,
                        "sources": sources_str,
                        "chat_id": context.chat_id,
                        "user_id": context.user_id,
                    }
                )
                # Check if high priority searches found results
                # Simple heuristic: if output contains "No" or "not found" or is very short, likely no results
                result_text = str(high_priority_result).lower()
                if len(result_text) > 100 and "no" not in result_text[:50] and "not found" not in result_text[:100]:
                    high_priority_found = True
                    logger.info("HIGH priority searches found results")
                else:
                    logger.info("HIGH priority searches found no results")
            except Exception as e:
                logger.warning(f"HIGH priority search execution had issues: {e}")
        
        # Phase 2: Build full task list with conditional LOW/VERY LOW searches
        tasks_to_execute = [coordination_task]
        search_tasks_context = [coordination_task]
        
        # Add HIGH priority tasks (already executed, but include in final task list)
        if search_strategy.memory.relevant and memory_priority == "high":
            tasks_to_execute.append(memory_search_task)
            search_tasks_context.append(memory_search_task)
        
        if search_strategy.tasks.relevant and tasks_priority == "high":
            tasks_to_execute.append(task_search_task)
            search_tasks_context.append(task_search_task)
        
        if search_strategy.lists.relevant and lists_priority == "high":
            tasks_to_execute.append(list_search_task)
            search_tasks_context.append(list_search_task)
        
        # Add MEDIUM priority tasks (always execute)
        if search_strategy.memory.relevant and memory_priority == "medium":
            logger.info("Adding MEDIUM priority: memory search")
            tasks_to_execute.append(memory_search_task)
            search_tasks_context.append(memory_search_task)
        
        if search_strategy.tasks.relevant and tasks_priority == "medium":
            logger.info("Adding MEDIUM priority: task search")
            tasks_to_execute.append(task_search_task)
            search_tasks_context.append(task_search_task)
        
        if search_strategy.lists.relevant and lists_priority == "medium":
            logger.info("Adding MEDIUM priority: list search")
            tasks_to_execute.append(list_search_task)
            search_tasks_context.append(list_search_task)
        
        # Conditionally add LOW/VERY LOW priority tasks
        if search_strategy.memory.relevant and memory_priority in ["low", "very low"]:
            if should_execute_search(memory_priority, high_priority_found):
                logger.info(f"Adding {memory_priority} priority: memory search")
                tasks_to_execute.append(memory_search_task)
                search_tasks_context.append(memory_search_task)
        
        if search_strategy.tasks.relevant and tasks_priority in ["low", "very low"]:
            if should_execute_search(tasks_priority, high_priority_found):
                logger.info(f"Adding {tasks_priority} priority: task search")
                tasks_to_execute.append(task_search_task)
                search_tasks_context.append(task_search_task)
        
        if search_strategy.lists.relevant and lists_priority in ["low", "very low"]:
            if should_execute_search(lists_priority, high_priority_found):
                logger.info(f"Adding {lists_priority} priority: list search")
                tasks_to_execute.append(list_search_task)
                search_tasks_context.append(list_search_task)
        
        # Update aggregation task context to only include executed searches
        aggregation_task.context = search_tasks_context
        tasks_to_execute.append(aggregation_task)
        
        logger.info(f"Final execution plan: {len(tasks_to_execute)} tasks total ({len(search_tasks_context) - 1} searches)")
        
        # Set tasks on the crew for final execution
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
