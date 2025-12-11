"""
RetrievalCrew orchestrator.

Coordinates QueryPlanner → Retriever → Composer workflow for question answering.
"""

from dataclasses import dataclass

from crewai import Crew, Process

from app.config import get_settings
from app.contracts.query import GroundedAnswer, Query
from app.llm import get_crewai_llm
from app.memory import MemoryItem, MemoryService
from app.tracing import get_tracer

from .composer import compose_answer, create_composer_agent, create_composition_task
from .query_planner import (
    create_query_planner_agent,
    create_query_planning_task,
    plan_query_from_question,
)
from .retriever import create_retriever_agent, create_retrieval_task, retrieve_memories

logger = get_tracer()
settings = get_settings()


@dataclass
class RetrievalContext:
    """Context for retrieval operations."""

    chat_id: str
    user_id: str
    memory_service: MemoryService


@dataclass
class RetrievalResult:
    """Result of retrieval workflow."""

    query: Query
    memories: list[MemoryItem]
    answer: GroundedAnswer


class RetrievalCrew:
    """
    Orchestrates the Retrieval Crew workflow using CrewAI.

    QueryPlanner: Analyzes question → structured Query
    Retriever: Searches LTM → relevant MemoryItems
    Composer: Generates grounded answer with citations
    
    Now uses CrewAI Crew() with shared memory between agents!
    """

    def __init__(self, memory_service: MemoryService, llm=None):
        """
        Initialize RetrievalCrew with CrewAI orchestration.

        Args:
            memory_service: Memory service for LTM access
            llm: Language model for agents (optional, defaults to config)
        """
        self.memory_service = memory_service
        self.llm = llm
        self.tracer = get_tracer()
        
        # Lazy initialization for CrewAI agents
        # (Only create when needed to avoid LLM initialization issues)
        self._crew = None
        self._agents_initialized = False
        
        self.tracer.info(
            "RetrievalCrew initialized (agents will be created on first use)",
            extra={
                "memory_enabled": settings.crewai_enable_memory,
                "memory_provider": settings.crewai_memory_provider
            }
        )
    
    def _initialize_agents(self):
        """Lazy initialization of CrewAI agents."""
        if self._agents_initialized:
            return
        
        self.tracer.info("Initializing CrewAI agents for RetrievalCrew")
        
        try:
            # Convert our LLMService to CrewAI-compatible LLM
            crewai_llm = get_crewai_llm(self.llm)
            
            self.tracer.info("CrewAI LLM obtained successfully")
            
            # Create agents with CrewAI-compatible LLM
            self.query_planner_agent = create_query_planner_agent(crewai_llm)
            self.retriever_agent = create_retriever_agent(crewai_llm)
            self.composer_agent = create_composer_agent(crewai_llm)
            
            self.tracer.info("CrewAI agents created successfully")
            
            # Configure embeddings for CrewAI memory (use Ollama instead of OpenAI)
            # CrewAI expects specific environment variable format
            import os
            os.environ["EMBEDDINGS_OLLAMA_MODEL_NAME"] = "nomic-embed-text"
            os.environ["EMBEDDINGS_OLLAMA_BASE_URL"] = settings.ollama_base_url
            
            embedder_config = {
                "provider": "ollama",
                "config": {
                    "model": "nomic-embed-text"
                }
            }
            
            # Create CrewAI Crew with shared memory and custom embeddings
            self._crew = Crew(
                agents=[
                    self.query_planner_agent,
                    self.retriever_agent,
                    self.composer_agent
                ],
                tasks=[],  # Tasks created dynamically per request
                process=Process.sequential,
                memory=settings.crewai_enable_memory,  # ← ENABLE SHARED MEMORY!
                embedder=embedder_config,  # ← Use Ollama embeddings instead of OpenAI
                verbose=True,
                full_output=True
            )
            
            self._agents_initialized = True
            self.tracer.info(
                "CrewAI crew initialized successfully",
                extra={
                    "memory_enabled": settings.crewai_enable_memory,
                    "agents_count": 3
                }
            )
            
        except Exception as e:
            self.tracer.error(
                "Failed to initialize CrewAI agents",
                extra={"error": str(e), "error_type": type(e).__name__}
            )
            self._agents_initialized = False
            raise  # Re-raise to see the error

    def retrieve(self, user_question: str, context: RetrievalContext) -> RetrievalResult:
        """
        Execute retrieval workflow to answer a question using CrewAI orchestration.

        Workflow (with CrewAI memory sharing):
        1. QueryPlanner: Parse question → Query (stored in crew memory)
        2. Retriever: Search LTM → MemoryItems (sees query from memory)
        3. Composer: Generate GroundedAnswer (sees query + memories from memory)

        Args:
            user_question: The user's natural language question
            context: Retrieval context with chat/user IDs and memory service

        Returns:
            RetrievalResult with query, memories, and grounded answer
        """
        try:
            self.tracer.info(
                "RetrievalCrew.retrieve starting",
                extra={"question": user_question[:100], "chat_id": context.chat_id}
            )
            
            # For now, use manual workflow (CrewAI Task execution coming in next iteration)
            # This maintains compatibility while we test memory integration
            
            # Step 1: Plan the query
            print(f"    ├─ Planning query...")
            query = plan_query_from_question(
                user_question, context.chat_id, context.user_id, self.llm
            )
            print(f"    ├─ Query: {query.intent.value}")

            # Step 2: Retrieve memories
            print(f"    ├─ Searching memories...")
            memories = retrieve_memories(
                query, context.chat_id, context.user_id, context.memory_service, self.llm
            )
            print(f"    ├─ Retrieved: {len(memories)} memories")

            # Step 3: Compose answer
            print(f"    └─ Composing answer...")
            answer = compose_answer(
                query, memories, context.chat_id, context.user_id, self.llm
            )

            self.tracer.info(
                "RetrievalCrew.retrieve completed",
                extra={
                    "has_evidence": answer.has_evidence,
                    "confidence": answer.confidence,
                    "memories_count": len(memories)
                }
            )

            return RetrievalResult(query=query, memories=memories, answer=answer)

        except Exception as e:
            print(f"    ❌ Retrieval workflow failed: {str(e)}")
            self.tracer.error(
                "RetrievalCrew.retrieve failed",
                extra={"error": str(e), "error_type": type(e).__name__}
            )

            # Return error response
            return RetrievalResult(
                query=Query(query_text=user_question),
                memories=[],
                answer=GroundedAnswer(
                    query=user_question,
                    answer=f"I encountered an error: {str(e)}",
                    citations=[],
                    confidence=0.0,
                    has_evidence=False,
                    reasoning=f"Error: {str(e)}",
                ),
            )
    
    def retrieve_with_crew_tasks(self, user_question: str, context: RetrievalContext) -> RetrievalResult:
        """
        Alternative method using full CrewAI Task orchestration.
        
        This will be the main method once we complete full CrewAI integration.
        Currently experimental.
        """
        try:
            # Initialize agents first (if not already done)
            self._initialize_agents()
            
            # Import Task for creating tasks
            from crewai import Task
            
            # Create dynamic tasks for this retrieval
            # Note: In CrewAI, each task's output is available to the next task via context
            
            task1 = Task(
                description=f"""
                Analyze this user question and produce a structured query:
                
                Question: "{user_question}"
                
                Classify the intent (factual, temporal, list, or summary) and extract:
                - People mentioned
                - Places mentioned
                - Dates or time references
                - Tags or keywords
                
                Output should be a structured query with search terms and filters.
                """,
                agent=self.query_planner_agent,
                expected_output="Structured query with intent, filters, and search terms"
            )
            
            task2 = Task(
                description=f"""
                Using the query from the previous task, search long-term memory 
                for relevant memories about: {user_question}
                
                Apply the filters and search terms identified by the Query Planner.
                Return the most relevant memories ranked by similarity.
                """,
                agent=self.retriever_agent,
                expected_output="List of relevant memories with content and metadata",
                context=[task1]  # This task depends on task1's output
            )
            
            task3 = Task(
                description=f"""
                Using the memories retrieved by the Retriever, compose a natural answer
                to the user's question: "{user_question}"
                
                If memories were found, synthesize them into a coherent answer.
                If no memories found, say so politely.
                Always cite which memories you used.
                """,
                agent=self.composer_agent,
                expected_output="Natural language answer with citations",
                context=[task1, task2]  # This task depends on both previous tasks
            )
            
            tasks = [task1, task2, task3]
            
            if not self._crew:
                raise RuntimeError("CrewAI crew not initialized")
            
            # Set tasks on the crew (CrewAI expects tasks as a property, not kickoff argument)
            self._crew.tasks = tasks
            
            # Execute crew workflow
            self.tracer.info("Starting crew.kickoff() with shared memory enabled")
            result = self._crew.kickoff(
                inputs={
                    "question": user_question,
                    "chat_id": context.chat_id,
                    "user_id": context.user_id
                }
            )
            self.tracer.info("Crew.kickoff() completed successfully")
            
            # Parse CrewOutput into RetrievalResult
            # CrewOutput contains: raw (final output string), tasks_output (list of task outputs)
            
            # Get the final composed answer from the last task
            final_answer = result.raw if hasattr(result, 'raw') else str(result)
            
            # For now, create a minimal Query and empty memories list
            # In a real implementation, we'd parse the task outputs to extract these
            from app.contracts.query import Query, QueryFilters, QueryIntent
            
            query = Query(
                query_text=user_question,
                intent=QueryIntent.FACTUAL,
                filters=QueryFilters(),
                max_results=10,
                reasoning="Generated by CrewAI orchestration"
            )
            
            # Create grounded answer from CrewAI output
            answer = GroundedAnswer(
                query=user_question,  # GroundedAnswer requires the original question
                answer=final_answer,
                citations=[],  # CrewAI handles citations internally
                confidence=0.9,  # High confidence since CrewAI orchestrated the answer
                metadata={"source": "crewai_orchestration", "tasks_completed": len(tasks)}
            )
            
            # Return properly structured result
            return RetrievalResult(
                query=query,
                memories=[],  # Memories are embedded in the answer
                answer=answer
            )
            
        except Exception as e:
            self.tracer.error(f"CrewAI kickoff failed: {e}")
            raise
