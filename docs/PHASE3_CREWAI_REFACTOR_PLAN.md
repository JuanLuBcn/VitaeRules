# Phase 3: CrewAI-First Refactoring Plan

**Date:** October 29, 2025  
**Objective:** Migrate from ConversationalOrchestrator to full CrewAI orchestration with shared memory and agent collaboration

---

## Executive Summary

This document outlines the complete refactoring strategy to migrate VitaeRules from the current **monolithic orchestrator** to a **CrewAI-first architecture** with:

1. ✅ **Specialized Agent Crews** - Each domain has a crew with smart agents
2. ✅ **Shared Memory** - CrewAI STM/LTM across agents in crews
3. ✅ **Agent Collaboration** - Automatic data passing and delegation
4. ✅ **Thin Orchestrator** - Routes to crews, manages conversation state
5. ✅ **Unified Search** - SearchAgent queries memory + tasks + lists
6. ✅ **Autonomous ChatAgent** - Has SearchAgent, always context-aware

**Migration Strategy:** Incremental, non-breaking, test-driven

---

## Current State Analysis

### What We Have ✅

```
ConversationalOrchestrator:
  ├─ Single LLM call analyzes everything
  ├─ Tools (ListTool, TaskTool) = Dumb DB operations
  ├─ RetrievalCrew (only crew currently used)
  ├─ Manual context management (self.contexts dict)
  └─ Orchestrator IS the bot personality

Current Crews (exist but not used by orchestrator):
  ├─ RetrievalCrew (QueryPlanner → Retriever → Composer)
  └─ CaptureCrew (Planner → Clarifier → ToolCaller)

Agents (CrewAI Agent objects):
  ├─ All agents have allow_delegation=False
  ├─ No memory=True on agents
  ├─ No Crew orchestration (manual workflow)
  └─ Agents are stateless functions, not intelligent
```

### What We're Missing ❌

```
CrewAI Features NOT Used:
  ❌ Crew() orchestration (no Crew objects instantiated)
  ❌ memory=True (no shared memory)
  ❌ allow_delegation (agents can't call each other)
  ❌ Hierarchical process (no manager agents)
  ❌ Agent collaboration (manual data passing)
  ❌ Task chaining (no Task objects)
  ❌ Automatic error handling & retries
  ❌ Built-in context accumulation

Architecture Gaps:
  ❌ No IntentDetectorAgent (orchestrator does it)
  ❌ No MemoryAgent (orchestrator calls tools directly)
  ❌ No TaskAgent (orchestrator calls tools directly)
  ❌ No ListAgent (orchestrator calls tools directly)
  ❌ No SearchAgent (no unified search)
  ❌ No ChatAgent (orchestrator handles chat)
  ❌ No context passing to agents
```

---

## Target Architecture (Phase 3)

### High-Level Design

```
┌────────────────────────────────────────────────────────┐
│           IntentOrchestrator (Thin Router)             │
│  - Detects intent (semantic, even low confidence)     │
│  - Routes to appropriate Crew                          │
│  - Manages conversation state (multi-turn)            │
│  - Minimal logic (just routing)                        │
└──────────────────┬─────────────────────────────────────┘
                   ↓
    ┌──────────────┼──────────────┬──────────────┐
    ↓              ↓               ↓              ↓
┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Memory  │  │   Task   │  │   List   │  │  Chat    │
│  Crew   │  │   Crew   │  │   Crew   │  │  Crew    │
└─────────┘  └──────────┘  └──────────┘  └──────────┘
     ↓             ↓              ↓             ↓
┌─────────────────────────────────────────────────────┐
│           RetrievalCrew (Unified Search)            │
│  - SearchAgent (memory + tasks + lists)            │
└─────────────────────────────────────────────────────┘
```

### Crew Architecture

#### 1. MemoryCrew (Store & Query)

**Purpose:** Handle all memory operations (store notes, query knowledge)

**Agents:**
```python
MemoryCrew:
  ├─ MemoryAnalyzerAgent
  │   Role: Analyze if message contains info to store or query
  │   Input: User message + context
  │   Output: Intent (store/query) + entities
  │   Memory: True (sees conversation)
  │   Delegation: Can delegate to SearchAgent
  │
  ├─ MemoryEnricherAgent
  │   Role: Enrich entities with context (people, places, time)
  │   Input: Entities from AnalyzerAgent
  │   Output: Enriched MemoryItem
  │   Memory: True
  │   Delegation: False
  │
  └─ MemoryStorerAgent
      Role: Validate and store in LTM, or query and return results
      Input: Enriched MemoryItem or search query
      Output: Success message or search results
      Memory: True
      Tools: MemoryTool (LTM operations)

Process: Sequential (Analyzer → Enricher → Storer)
Memory: Shared STM across agents
```

**Implementation:**
```python
# src/app/crews/memory/crew.py

from crewai import Crew, Agent, Task, Process
from crewai.memory import ShortTermMemory, LongTermMemory

class MemoryCrew:
    def __init__(self, memory_service, llm):
        self.memory_service = memory_service
        self.llm = llm
        
        # Create agents
        self.analyzer = Agent(
            role="Memory Analyzer",
            goal="Determine if user wants to store or query information",
            backstory="Expert at understanding user intent for memory operations",
            llm=llm,
            memory=True,
            allow_delegation=True,
            verbose=True
        )
        
        self.enricher = Agent(
            role="Memory Enricher",
            goal="Extract and enrich entities from user message",
            backstory="Specialist in NLP entity extraction and context enrichment",
            llm=llm,
            memory=True,
            allow_delegation=False,
            verbose=True
        )
        
        self.storer = Agent(
            role="Memory Manager",
            goal="Store enriched information or retrieve stored knowledge",
            backstory="Database expert managing long-term knowledge storage",
            llm=llm,
            memory=True,
            tools=[MemoryTool(memory_service)],
            allow_delegation=False,
            verbose=True
        )
        
        # Create crew with shared memory
        self.crew = Crew(
            agents=[self.analyzer, self.enricher, self.storer],
            tasks=[],  # Tasks created dynamically per request
            process=Process.sequential,
            memory=True,  # ← ENABLE SHARED MEMORY!
            verbose=True
        )
    
    async def process(self, message: str, context: dict) -> dict:
        """Process memory operation (store or query)."""
        
        # Create dynamic tasks
        tasks = [
            Task(
                description=f"Analyze this message and determine intent (store/query): '{message}'",
                agent=self.analyzer,
                expected_output="Intent (store/query) and extracted entities"
            ),
            Task(
                description="Enrich entities with context (people, places, temporal info)",
                agent=self.enricher,
                expected_output="Enriched MemoryItem with all metadata"
            ),
            Task(
                description="Store in long-term memory or execute search query",
                agent=self.storer,
                expected_output="Success message or search results"
            )
        ]
        
        # Execute crew workflow
        result = self.crew.kickoff(
            inputs={
                "message": message,
                "context": context,
                "chat_id": context.get("chat_id"),
                "user_id": context.get("user_id")
            },
            tasks=tasks
        )
        
        return result
```

---

#### 2. TaskCrew (Create & Manage Tasks)

**Purpose:** Handle task operations (create, complete, list, update)

**Agents:**
```python
TaskCrew:
  ├─ TaskAnalyzerAgent
  │   Role: Understand what task user wants to create/manage
  │   Input: User message + context
  │   Output: Task intent (create/complete/list) + entities
  │   Memory: True
  │   Delegation: False
  │
  ├─ TaskValidatorAgent
  │   Role: Check if have required info (title), smart defaults for optional (time, list)
  │   Input: Entities from AnalyzerAgent
  │   Output: Validated TaskData or clarification question
  │   Memory: True
  │   Delegation: False
  │
  └─ TaskExecutorAgent
      Role: Execute task operation (create/complete/list)
      Input: Validated TaskData
      Output: Success message with task details
      Memory: True
      Tools: TaskTool

Process: Sequential (Analyzer → Validator → Executor)
Memory: Shared STM
```

**Key Feature:** Smart defaults - if time not specified, uses null (no reminder)

---

#### 3. ListCrew (Manage Lists)

**Purpose:** Handle list operations (create, add, remove, list)

**Agents:**
```python
ListCrew:
  ├─ ListAnalyzerAgent
  │   Role: Determine list operation (add/remove/create/delete)
  │   Input: User message + context
  │   Output: List intent + items + list_name (can infer from context)
  │   Memory: True
  │   Delegation: False
  │
  └─ ListExecutorAgent
      Role: Execute list operation with smart list_name inference
      Input: List operation + items
      Output: Success message
      Memory: True
      Tools: ListTool

Process: Sequential (Analyzer → Executor)
Memory: Shared STM
```

**Key Feature:** List name inference from context or common patterns (compra, trabajo, etc.)

---

#### 4. RetrievalCrew (Unified Search) ⭐

**Purpose:** Search across ALL sources (memory + tasks + lists)

**Current State:** Already exists, needs enhancement for unified search

**Enhanced Agents:**
```python
RetrievalCrew (Enhanced):
  ├─ QueryPlannerAgent
  │   Role: Analyze question and plan search strategy
  │   Input: User question + context
  │   Output: SearchQuery with sources (memory/tasks/lists)
  │   Memory: True
  │   Delegation: False
  │
  ├─ UnifiedSearchAgent ← NEW!
  │   Role: Search across multiple sources in parallel
  │   Input: SearchQuery
  │   Output: Combined results from memory + tasks + lists
  │   Memory: True
  │   Tools: [MemorySearchTool, TaskSearchTool, ListSearchTool]
  │   Delegation: False
  │
  └─ ComposerAgent
      Role: Synthesize answer from all results with citations
      Input: Combined search results
      Output: Grounded answer with source citations
      Memory: True
      Delegation: False

Process: Sequential (Planner → Search → Compose)
Memory: Shared STM
```

**Key Feature:** Unified search - one query searches ALL data sources!

---

#### 5. ChatCrew (Context-Aware Conversation) ⭐

**Purpose:** Handle general conversation with automatic context search

**Agents:**
```python
ChatCrew:
  ├─ ContextAnalyzerAgent
  │   Role: Determine if need to search for context before responding
  │   Input: User message
  │   Output: Decision (search/no-search) + search query if needed
  │   Memory: True
  │   Delegation: Can delegate to RetrievalCrew.UnifiedSearchAgent
  │
  └─ ConversationAgent
      Role: Generate natural response, context-aware if search results available
      Input: User message + optional search results
      Output: Natural conversational response
      Memory: True
      Delegation: True (can call ContextAnalyzer)

Process: Sequential (ContextAnalyzer → Conversation)
Memory: Shared STM
```

**Key Feature:** ALWAYS searches for context before responding!

**Implementation:**
```python
# src/app/crews/chat/crew.py

class ChatCrew:
    def __init__(self, llm, retrieval_crew):
        self.llm = llm
        self.retrieval_crew = retrieval_crew  # ← Has UnifiedSearchAgent!
        
        self.context_analyzer = Agent(
            role="Context Analyzer",
            goal="Determine if conversation needs context from stored data",
            llm=llm,
            memory=True,
            allow_delegation=True,  # ← Can delegate to retrieval_crew!
            verbose=True
        )
        
        self.conversation_agent = Agent(
            role="Conversationalist",
            goal="Provide natural, context-aware responses",
            llm=llm,
            memory=True,
            allow_delegation=False,
            verbose=True
        )
        
        self.crew = Crew(
            agents=[self.context_analyzer, self.conversation_agent],
            process=Process.sequential,
            memory=True,
            verbose=True
        )
    
    async def chat(self, message: str, context: dict) -> dict:
        """Process chat message with automatic context search."""
        
        # Task 1: Check if need context
        search_task = Task(
            description=f"Analyze if this message needs context: '{message}'. If yes, search all sources.",
            agent=self.context_analyzer,
            expected_output="Search results or indication no search needed"
        )
        
        # Task 2: Generate response
        response_task = Task(
            description="Generate natural response using search results if available",
            agent=self.conversation_agent,
            expected_output="Natural conversational response"
        )
        
        result = self.crew.kickoff(
            inputs={"message": message, "context": context},
            tasks=[search_task, response_task]
        )
        
        return result
```

---

#### 6. IntentOrchestrator (Thin Router)

**Purpose:** Detect intent and route to appropriate crew

**Not a Crew!** Just a router that:
1. Detects intent (semantic, fast, single LLM call)
2. Routes to the right crew
3. Manages multi-turn conversations
4. Passes context to crews

**Implementation:**
```python
# src/app/agents/intent_orchestrator.py

from crewai import Agent

class IntentOrchestrator:
    """
    Thin router - detects intent and routes to crews.
    
    NOT a crew itself - just a lightweight coordinator.
    """
    
    def __init__(self, llm, memory_service):
        self.llm = llm
        self.memory_service = memory_service
        self.contexts = {}  # Multi-turn conversation state
        
        # Initialize all crews
        self.memory_crew = MemoryCrew(memory_service, llm)
        self.task_crew = TaskCrew(llm)
        self.list_crew = ListCrew(llm)
        self.retrieval_crew = RetrievalCrew(memory_service, llm)  # Enhanced
        self.chat_crew = ChatCrew(llm, self.retrieval_crew)
        
        # Intent detection agent (standalone, not in crew)
        self.intent_detector = Agent(
            role="Intent Detector",
            goal="Quickly detect user intent from message",
            backstory="Expert at semantic intent classification",
            llm=llm,
            memory=False,  # Stateless
            allow_delegation=False,
            verbose=False
        )
    
    async def handle_message(self, message: str, chat_id: str, user_id: str) -> dict:
        """
        Main entry point - routes message to appropriate crew.
        """
        # Get conversation context
        context = self._get_context(chat_id)
        context.update({
            "chat_id": chat_id,
            "user_id": user_id,
            "message": message
        })
        
        # Check if mid-conversation (waiting for answer)
        if context.get("waiting_for"):
            # Route back to crew that asked question
            return await self._continue_conversation(message, context)
        
        # Detect intent (fast, single LLM call, semantic only)
        intent = await self._detect_intent(message, context)
        
        # Route to crew (crew decides if needs more info)
        return await self._route_to_crew(intent, message, context)
    
    async def _detect_intent(self, message: str, context: dict) -> str:
        """
        Semantic intent detection (no examples, just meaning).
        
        Returns: Intent enum (MEMORY_STORE, MEMORY_QUERY, TASK_CREATE, 
                              LIST_ADD, CHAT, etc.)
        """
        prompt = f"""Analiza el propósito semántico de este mensaje:

Mensaje: "{message}"

Contexto reciente: {context.get('recent_intents', [])}

Propósito:
- ¿Está AFIRMANDO información nueva para guardar? → MEMORY_STORE
- ¿Está PREGUNTANDO por info que ÉL guardó antes? → MEMORY_QUERY
- ¿Pide RECORDATORIO futuro? → TASK_CREATE
- ¿Pregunta QUÉ tareas/recordatorios tiene? → TASK_QUERY
- ¿AÑADE items a lista? → LIST_ADD
- ¿Pregunta QUÉ hay en lista? → LIST_QUERY
- ¿CONVERSACIÓN general? → CHAT

NO uses keywords. Solo semántica pura.

Responde SOLO el intent: MEMORY_STORE | MEMORY_QUERY | TASK_CREATE | TASK_QUERY | LIST_ADD | LIST_QUERY | CHAT
"""
        
        response = await self.llm.generate(prompt)
        intent = response.strip()
        
        # Save to context
        context.setdefault('recent_intents', []).append(intent)
        if len(context['recent_intents']) > 3:
            context['recent_intents'] = context['recent_intents'][-3:]
        
        return intent
    
    async def _route_to_crew(self, intent: str, message: str, context: dict) -> dict:
        """Route to appropriate crew based on intent."""
        
        if intent in ["MEMORY_STORE", "MEMORY_QUERY"]:
            return await self.memory_crew.process(message, context)
        
        elif intent in ["TASK_CREATE", "TASK_COMPLETE", "TASK_QUERY"]:
            return await self.task_crew.process(message, context)
        
        elif intent in ["LIST_ADD", "LIST_REMOVE", "LIST_QUERY"]:
            return await self.list_crew.process(message, context)
        
        elif intent == "CHAT":
            return await self.chat_crew.chat(message, context)
        
        else:
            # Unknown intent → fallback to chat
            return await self.chat_crew.chat(message, context)
    
    def _get_context(self, chat_id: str) -> dict:
        """Get or create conversation context."""
        if chat_id not in self.contexts:
            self.contexts[chat_id] = {
                "recent_intents": [],
                "recent_entities": {},
                "waiting_for": None,
                "active_crew": None
            }
        return self.contexts[chat_id]
    
    async def _continue_conversation(self, message: str, context: dict) -> dict:
        """Continue multi-turn conversation with active crew."""
        active_crew = context.get("active_crew")
        
        if active_crew == "memory":
            return await self.memory_crew.process(message, context)
        elif active_crew == "task":
            return await self.task_crew.process(message, context)
        elif active_crew == "list":
            return await self.list_crew.process(message, context)
        else:
            # Fallback
            return await self.chat_crew.chat(message, context)
```

---

## CrewAI Features We'll Use

### 1. Shared Memory ⭐

**Feature:** `memory=True` on Crew

**Benefit:** All agents in crew see conversation context automatically

**Implementation:**
```python
crew = Crew(
    agents=[agent1, agent2, agent3],
    memory=True,  # ← Enables STM/LTM sharing
    verbose=True
)

# What it does:
# - Agent1 extracts entities → Stored in STM
# - Agent2 automatically sees Agent1's entities
# - Agent3 sees everything from Agent1 and Agent2
# - NO manual context passing needed!
```

**Types of Memory:**
```python
from crewai.memory import ShortTermMemory, LongTermMemory, EntityMemory

# Short-Term Memory (conversation context)
# - Stores recent messages/actions in crew execution
# - Bounded window (configurable)
# - Per-crew instance

# Long-Term Memory (learnings over time)
# - Vector embeddings (ChromaDB/FAISS)
# - Semantic search
# - Persists across executions

# Entity Memory (people, places, things)
# - Tracks entities mentioned
# - Builds relationship graph
# - Contextual understanding
```

**Our Usage:**
```python
# Enable all memory types for each crew
crew = Crew(
    agents=[...],
    memory=True,  # ← Enables all types
    memory_config={
        "provider": "chroma",  # Use ChromaDB (we already have it!)
        "collection_name": f"crew_{crew_name}",
        "embedding_model": "all-MiniLM-L6-v2"  # Same as our LTM
    }
)
```

---

### 2. Agent Delegation ⭐

**Feature:** `allow_delegation=True` on Agent

**Benefit:** Agents can call other agents for help

**Implementation:**
```python
main_agent = Agent(
    role="Main Agent",
    goal="Handle user request",
    allow_delegation=True,  # ← Can delegate!
    llm=llm
)

specialist_agent = Agent(
    role="Date Parser",
    goal="Parse complex dates",
    allow_delegation=False,
    llm=llm
)

crew = Crew(agents=[main_agent, specialist_agent])

# Flow:
# User: "Recuérdame el próximo martes"
# ↓
# Main Agent: "Hmm, 'próximo martes' is complex..."
#   → Delegates to → Specialist Agent
# ↓
# Specialist: "próximo martes = 2025-11-04"
#   → Returns to → Main Agent
# ↓
# Main Agent: Creates task with date "2025-11-04"
```

**Our Usage:**
```python
# ChatAgent delegates to SearchAgent
chat_agent = Agent(
    role="Conversationalist",
    allow_delegation=True,  # ← Can call SearchAgent!
    llm=llm
)

search_agent = Agent(
    role="Search Specialist",
    allow_delegation=False,
    llm=llm,
    tools=[UnifiedSearchTool()]
)

# Flow:
# User: "¿Dónde es el partido?"
# ↓
# ChatAgent: "Need context..."
#   → Delegates to → SearchAgent
# ↓
# SearchAgent: Searches → Returns results
#   → Returns to → ChatAgent
# ↓
# ChatAgent: "El partido es en club Laietà"
```

---

### 3. Task Chaining

**Feature:** Define Task objects with dependencies

**Benefit:** Automatic sequential execution with output passing

**Implementation:**
```python
task1 = Task(
    description="Extract entities from message",
    agent=analyzer_agent,
    expected_output="Entities dict"
)

task2 = Task(
    description="Enrich entities with context",
    agent=enricher_agent,
    expected_output="Enriched entities",
    context=[task1]  # ← Depends on task1 output!
)

task3 = Task(
    description="Store in database",
    agent=storer_agent,
    expected_output="Success message",
    context=[task2]  # ← Depends on task2 output!
)

crew = Crew(
    agents=[analyzer_agent, enricher_agent, storer_agent],
    tasks=[task1, task2, task3],
    process=Process.sequential  # ← One after another
)
```

---

### 4. Process Types

**Feature:** Sequential vs Hierarchical workflows

**Sequential Process:**
```python
crew = Crew(
    agents=[agent1, agent2, agent3],
    tasks=[task1, task2, task3],
    process=Process.sequential  # ← Linear flow
)

# Flow: agent1 → agent2 → agent3
```

**Hierarchical Process:**
```python
manager_agent = Agent(
    role="Manager",
    goal="Coordinate team",
    allow_delegation=True
)

worker1 = Agent(role="Worker 1")
worker2 = Agent(role="Worker 2")

crew = Crew(
    agents=[manager_agent, worker1, worker2],
    tasks=[task1, task2],
    process=Process.hierarchical,  # ← Manager delegates
    manager_llm=llm
)

# Flow:
# Manager analyzes → Delegates task1 to worker1
#                  → Delegates task2 to worker2 (parallel!)
#                  → Aggregates results
```

**Our Usage:** Sequential for most crews, maybe hierarchical for CaptureCrew later

---

### 5. Tools Integration

**Feature:** Attach tools to agents

**Benefit:** Agents can execute actions directly

**Implementation:**
```python
from crewai import Agent, Tool

# Define tool
search_tool = Tool(
    name="search_memory",
    description="Search long-term memory for information",
    func=lambda query: memory_service.search(query)
)

# Attach to agent
agent = Agent(
    role="Memory Agent",
    tools=[search_tool],  # ← Agent can use this tool
    llm=llm
)
```

**Our Usage:**
```python
# Each executor agent has its domain tools

memory_agent = Agent(
    role="Memory Manager",
    tools=[MemoryTool(memory_service)],
    llm=llm
)

task_agent = Agent(
    role="Task Executor",
    tools=[TaskTool()],
    llm=llm
)

search_agent = Agent(
    role="Unified Search",
    tools=[
        MemorySearchTool(memory_service),
        TaskSearchTool(),
        ListSearchTool()
    ],
    llm=llm
)
```

---

### 6. Error Handling & Retries

**Feature:** Built-in error handling

**Benefit:** Automatic retries on failure

**Implementation:**
```python
crew = Crew(
    agents=[...],
    tasks=[...],
    max_rpm=10,  # Rate limit
    max_retries=3,  # Retry failed tasks
    verbose=True
)
```

---

### 7. Observability

**Feature:** Built-in logging and tracing

**Benefit:** See what agents are doing

**Implementation:**
```python
crew = Crew(
    agents=[...],
    tasks=[...],
    verbose=True  # ← Detailed logs
)

# Output:
# [Agent: Memory Analyzer] Starting task: Extract entities...
# [Agent: Memory Analyzer] Found entities: {...}
# [Agent: Memory Enricher] Starting task: Enrich with context...
# [Agent: Memory Enricher] Enriched: {...}
# [Agent: Memory Storer] Starting task: Store in LTM...
# [Agent: Memory Storer] Stored successfully: memory_123
```

---

## Migration Plan (Incremental)

### Phase 3.1: Enable CrewAI Memory on Existing Crews (Week 1)

**Goal:** Add `memory=True` to existing crews without changing orchestrator

**Changes:**
1. RetrievalCrew: Enable memory
2. CaptureCrew: Enable memory
3. Test that memory sharing works

**Implementation:**
```python
# src/app/crews/retrieval/crew.py

class RetrievalCrew:
    def __init__(self, memory_service, llm):
        # ... existing code ...
        
        # Create Crew object (NEW!)
        self.crew = Crew(
            agents=[
                self.query_planner_agent,
                self.retriever_agent,
                self.composer_agent
            ],
            process=Process.sequential,
            memory=True,  # ← ENABLE MEMORY!
            memory_config={
                "provider": "chroma",
                "collection_name": "retrieval_crew",
                "embedding_model": "all-MiniLM-L6-v2"
            },
            verbose=True
        )
    
    def retrieve(self, question, context):
        # Use crew.kickoff instead of manual workflow
        tasks = [
            Task(
                description=f"Plan query for: {question}",
                agent=self.query_planner_agent,
                expected_output="Query plan"
            ),
            Task(
                description="Search memory for relevant information",
                agent=self.retriever_agent,
                expected_output="List of memory items"
            ),
            Task(
                description="Compose grounded answer with citations",
                agent=self.composer_agent,
                expected_output="Grounded answer"
            )
        ]
        
        result = self.crew.kickoff(
            inputs={"question": question, "context": context},
            tasks=tasks
        )
        
        return result
```

**Testing:**
- Verify agents see each other's outputs
- Check memory persistence across calls
- Ensure no regressions

---

### Phase 3.2: Create UnifiedSearchAgent (Week 1-2)

**Goal:** Enable searching across memory + tasks + lists

**New Files:**
```
src/app/crews/retrieval/
  ├─ unified_search_agent.py  ← NEW
  └─ tools/
      ├─ memory_search_tool.py  ← NEW
      ├─ task_search_tool.py    ← NEW
      └─ list_search_tool.py    ← NEW
```

**Implementation:**
```python
# src/app/crews/retrieval/unified_search_agent.py

from crewai import Agent, Tool

class UnifiedSearchAgent:
    """Agent that searches across all data sources."""
    
    def __init__(self, memory_service, llm):
        self.memory_service = memory_service
        
        # Create tools
        self.memory_tool = Tool(
            name="search_memory",
            description="Search long-term memory (notes, events)",
            func=self._search_memory
        )
        
        self.task_tool = Tool(
            name="search_tasks",
            description="Search tasks and reminders",
            func=self._search_tasks
        )
        
        self.list_tool = Tool(
            name="search_lists",
            description="Search list items",
            func=self._search_lists
        )
        
        # Create agent
        self.agent = Agent(
            role="Unified Search Specialist",
            goal="Search all data sources and combine results",
            backstory="Expert at parallel search across multiple databases",
            llm=llm,
            tools=[self.memory_tool, self.task_tool, self.list_tool],
            memory=True,
            allow_delegation=False,
            verbose=True
        )
    
    async def _search_memory(self, query: str) -> list:
        """Search long-term memory."""
        results = await self.memory_service.search(query)
        return [{"type": "memory", "data": r} for r in results]
    
    async def _search_tasks(self, query: str) -> list:
        """Search tasks."""
        # Use TaskTool to search
        from app.tools.task_tool import TaskTool
        tool = TaskTool()
        results = await tool.execute({
            "operation": "search_tasks",
            "query": query
        })
        return [{"type": "task", "data": r} for r in results]
    
    async def _search_lists(self, query: str) -> list:
        """Search lists."""
        # Use ListTool to search
        from app.tools.list_tool import ListTool
        tool = ListTool()
        results = await tool.execute({
            "operation": "search_lists",
            "query": query
        })
        return [{"type": "list", "data": r} for r in results]
    
    async def search(self, query: str, sources: list[str] = None) -> dict:
        """
        Execute unified search.
        
        Args:
            query: Search query
            sources: List of sources to search (default: all)
                     ["memory", "tasks", "lists"]
        
        Returns:
            Combined results from all sources
        """
        if sources is None:
            sources = ["memory", "tasks", "lists"]
        
        # Search all sources in parallel
        results = {
            "memory": [],
            "tasks": [],
            "lists": []
        }
        
        if "memory" in sources:
            results["memory"] = await self._search_memory(query)
        if "tasks" in sources:
            results["tasks"] = await self._search_tasks(query)
        if "lists" in sources:
            results["lists"] = await self._search_lists(query)
        
        return results
```

**Integration:**
```python
# src/app/crews/retrieval/crew.py

class RetrievalCrew:
    def __init__(self, memory_service, llm):
        # ... existing agents ...
        
        # Add UnifiedSearchAgent
        self.unified_search = UnifiedSearchAgent(memory_service, llm)
        
        # Update crew
        self.crew = Crew(
            agents=[
                self.query_planner_agent,
                self.unified_search.agent,  # ← NEW!
                self.composer_agent
            ],
            # ...
        )
```

**Testing:**
- Search for memory item → Found ✅
- Search for task → Found ✅
- Search for list item → Found ✅
- Search query finds items across multiple sources ✅

---

### Phase 3.3: Create ChatCrew with UnifiedSearch (Week 2)

**Goal:** Autonomous chat agent that always searches for context

**New Files:**
```
src/app/crews/chat/
  ├─ __init__.py
  ├─ crew.py        ← NEW
  └─ agents.py      ← NEW
```

**Implementation:** (See ChatCrew architecture section above)

**Integration:**
```python
# src/app/agents/orchestrator.py (current)

class ConversationalOrchestrator:
    def __init__(self, llm, memory):
        # ... existing code ...
        
        # Add ChatCrew
        self.chat_crew = ChatCrew(llm, self.retrieval_crew)
    
    async def _analyze_message(self, message):
        # ... existing code ...
        
        # If intent is CHAT, use ChatCrew
        if analysis.get("intent") == "CHAT":
            result = await self.chat_crew.chat(
                message=message,
                context={"chat_id": chat_id, "user_id": user_id}
            )
            return result
```

**Testing:**
- Chat message → Searches for context → Responds with context ✅
- Chat without context → Responds naturally ✅
- Multi-turn chat maintains context (CrewAI memory) ✅

---

### Phase 3.4: Create MemoryCrew (Week 2-3)

**Goal:** Smart memory operations with enrichment

**New Files:**
```
src/app/crews/memory/
  ├─ __init__.py
  ├─ crew.py        ← NEW
  └─ agents.py      ← NEW
```

**Implementation:** (See MemoryCrew architecture section above)

**Integration:**
```python
# src/app/agents/orchestrator.py

class ConversationalOrchestrator:
    def __init__(self, llm, memory):
        # Add MemoryCrew
        self.memory_crew = MemoryCrew(memory, llm)
    
    async def _handle_new_request(self, message, media_ref, chat_id, user_id):
        # ... detect intent ...
        
        if intent in ["MEMORY_STORE", "MEMORY_QUERY"]:
            result = await self.memory_crew.process(
                message=message,
                context={
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "media_ref": media_ref
                }
            )
            return result
```

**Testing:**
- Store note → Enriched → Stored ✅
- Query note → Found with context ✅
- Multi-turn enrichment (asks question, gets answer, stores) ✅

---

### Phase 3.5: Create TaskCrew & ListCrew (Week 3)

**Goal:** Smart task/list operations with validation

**Implementation:** Similar to MemoryCrew

**Testing:**
- Create task with all info → Direct execution ✅
- Create task missing time → Uses null (no reminder) ✅
- Add to list without list name → Infers from context ✅
- List tasks → Direct query (no analysis needed) ✅

---

### Phase 3.6: Replace Orchestrator with IntentOrchestrator (Week 4)

**Goal:** Thin router that just detects intent and routes to crews

**Implementation:**
```python
# src/app/agents/intent_orchestrator.py (NEW)
# See IntentOrchestrator section above
```

**Migration:**
```python
# src/adapters/telegram_bot.py

from app.agents.intent_orchestrator import IntentOrchestrator

class TelegramAdapter:
    def __init__(self):
        # OLD:
        # self.orchestrator = ConversationalOrchestrator(llm, memory)
        
        # NEW:
        self.orchestrator = IntentOrchestrator(llm, memory)
    
    async def handle_message(self, message):
        # Same interface, different implementation!
        result = await self.orchestrator.handle_message(
            message=message,
            chat_id=chat_id,
            user_id=user_id
        )
        return result
```

**Testing:**
- All existing flows work ✅
- Intent detection accurate ✅
- Crews receive context ✅
- Multi-turn conversations work ✅

---

### Phase 3.7: Enable Agent Delegation (Week 5)

**Goal:** ChatAgent can delegate to SearchAgent

**Changes:**
```python
# src/app/crews/chat/crew.py

class ChatCrew:
    def __init__(self, llm, retrieval_crew):
        self.context_analyzer = Agent(
            role="Context Analyzer",
            allow_delegation=True,  # ← ENABLE!
            llm=llm
        )
        
        # Can now delegate to UnifiedSearchAgent
```

**Testing:**
- ChatAgent asks question → Delegates to SearchAgent → Gets results → Responds ✅

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_memory_crew.py

async def test_memory_crew_stores_note():
    crew = MemoryCrew(memory_service, llm)
    
    result = await crew.process(
        message="María vive en Barcelona",
        context={"chat_id": "test", "user_id": "user1"}
    )
    
    assert result["status"] == "success"
    assert "guardado" in result["message"].lower()
    
    # Verify stored in LTM
    items = memory_service.search("María Barcelona")
    assert len(items) > 0


async def test_memory_crew_enriches_entities():
    crew = MemoryCrew(memory_service, llm)
    
    result = await crew.process(
        message="Partido padel mañana 18:00 club Laietà",
        context={"chat_id": "test", "user_id": "user1"}
    )
    
    # Verify enrichment added temporal context
    items = memory_service.search("partido padel")
    assert items[0].event_start_at is not None
    assert items[0].location == "club Laietà"
```

### Integration Tests

```python
# tests/integration/test_orchestrator_crews.py

async def test_full_flow_memory_storage():
    """Test orchestrator → MemoryCrew → Storage"""
    orchestrator = IntentOrchestrator(llm, memory_service)
    
    # User stores note
    result = await orchestrator.handle_message(
        message="Anota que María vive en Barcelona",
        chat_id="test",
        user_id="user1"
    )
    
    assert result["status"] == "success"
    
    # Later, user queries
    result = await orchestrator.handle_message(
        message="¿Dónde vive María?",
        chat_id="test",
        user_id="user1"
    )
    
    assert "Barcelona" in result["message"]


async def test_chat_with_context_search():
    """Test ChatCrew automatically searches for context"""
    orchestrator = IntentOrchestrator(llm, memory_service)
    
    # Store context
    await orchestrator.handle_message(
        message="El partido de padel es el 29 de octubre en club Laietà",
        chat_id="test",
        user_id="user1"
    )
    
    # Ask question (chat intent)
    result = await orchestrator.handle_message(
        message="¿Dónde es el partido?",
        chat_id="test",
        user_id="user1"
    )
    
    # Should find context and answer
    assert "club Laietà" in result["message"].lower()
```

### End-to-End Tests

```python
# tests/e2e/test_conversation_flows.py

async def test_multi_turn_task_creation():
    """Test multi-turn conversation for task creation"""
    orchestrator = IntentOrchestrator(llm, memory_service)
    
    # Turn 1: User mentions task
    result = await orchestrator.handle_message(
        message="Recuérdame algo",
        chat_id="test",
        user_id="user1"
    )
    assert result["waiting_for_input"] == True
    assert "qué" in result["message"].lower()
    
    # Turn 2: User provides task
    result = await orchestrator.handle_message(
        message="Llamar a Juan",
        chat_id="test",
        user_id="user1"
    )
    assert result["waiting_for_input"] == True
    assert "cuándo" in result["message"].lower()
    
    # Turn 3: User provides time
    result = await orchestrator.handle_message(
        message="Mañana a las 3pm",
        chat_id="test",
        user_id="user1"
    )
    assert result["waiting_for_input"] == False
    assert "listo" in result["message"].lower()
```

---

## Benefits Summary

### What We Gain ✅

1. **Automatic Context Sharing**
   - Agents see each other's outputs (no manual passing)
   - Conversation context persists across crew execution
   - Entity tracking automatic

2. **Agent Collaboration**
   - Agents can delegate to specialists
   - ChatAgent delegates to SearchAgent
   - Manager agents can coordinate workers

3. **Unified Search**
   - One query searches memory + tasks + lists
   - No more data silos
   - Context-aware chat responses

4. **Cleaner Architecture**
   - Orchestrator = Just routing (150 lines)
   - Each crew = Domain expert (200 lines each)
   - Easy to extend (add new crew without touching orchestrator)

5. **Better Conversation Flow**
   - Multi-turn handled by crews
   - Each crew decides if needs more info
   - Smart defaults reduce questions

6. **Built-in Features**
   - Error handling & retries
   - Logging & observability
   - Memory persistence
   - Rate limiting

### Comparison: Before vs After

| Feature | Current (Phase 2) | After (Phase 3) |
|---------|-------------------|-----------------|
| Orchestrator | Monolithic (1177 lines) | Thin router (150 lines) |
| Intent Detection | In orchestrator | Separate agent |
| Agents | Dumb tools (DB ops) | Smart crews (LLM + logic) |
| Context Sharing | Manual (self.contexts) | Automatic (CrewAI memory) |
| Search | Memory only | Memory + Tasks + Lists |
| ChatAgent | Part of orchestrator | Autonomous crew with search |
| Multi-turn | Manual state management | Crew handles automatically |
| Extensibility | Hard (modify orchestrator) | Easy (add new crew) |
| Testing | Hard (monolithic) | Easy (test each crew) |
| Observability | Manual logging | Built-in crew logs |

---

## Risks & Mitigation

### Risk 1: Performance (Multiple LLM Calls)

**Current:** 1 LLM call per message  
**Phase 3:** 2-3 LLM calls per message (intent + crew)

**Mitigation:**
- Use smaller models for intent detection (fast)
- Cache common intents
- Parallel execution where possible
- Monitor latency, optimize hot paths

---

### Risk 2: Complexity

**Current:** One file, simple logic  
**Phase 3:** Multiple crews, more files

**Mitigation:**
- Clear documentation (this file!)
- Consistent patterns across crews
- Good test coverage
- Gradual migration (incremental phases)

---

### Risk 3: CrewAI Learning Curve

**Current:** No CrewAI features used  
**Phase 3:** Heavy CrewAI usage

**Mitigation:**
- Start with simple crews (ChatCrew)
- Learn incrementally (one feature at a time)
- Reference docs and examples
- This document has implementation examples

---

### Risk 4: Breaking Changes

**Current:** Working system  
**Phase 3:** Complete refactor

**Mitigation:**
- Incremental migration (7 phases)
- Keep ConversationalOrchestrator during migration
- Test each phase thoroughly
- Feature flags for rollback

---

## Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| 3.1 | 3 days | CrewAI memory on existing crews |
| 3.2 | 4 days | UnifiedSearchAgent |
| 3.3 | 3 days | ChatCrew with search |
| 3.4 | 5 days | MemoryCrew |
| 3.5 | 5 days | TaskCrew & ListCrew |
| 3.6 | 4 days | IntentOrchestrator |
| 3.7 | 2 days | Agent delegation |
| Testing | 4 days | Full test suite |
| **Total** | **30 days** | **Phase 3 Complete** |

---

## Success Criteria

### Functional

- ✅ All existing flows work (tasks, lists, memory, queries)
- ✅ Unified search finds items across all sources
- ✅ ChatAgent always context-aware
- ✅ Multi-turn conversations work smoothly
- ✅ Smart defaults reduce questions
- ✅ Agent delegation works (ChatAgent → SearchAgent)

### Technical

- ✅ All crews use `memory=True`
- ✅ Test coverage >80%
- ✅ Orchestrator <200 lines
- ✅ Each crew <250 lines
- ✅ Response time <2s p95
- ✅ Zero regressions

### User Experience

- ✅ Faster responses (fewer questions)
- ✅ Better context awareness
- ✅ More accurate search results
- ✅ Natural conversation flow
- ✅ Fewer "I don't understand" responses

---

## Future Enhancements (Post-Phase 3)

### Phase 4: Advanced Features

1. **Hierarchical Process**
   - Manager agent coordinates crews
   - Parallel execution where possible

2. **Progressive Enrichment**
   - Enricher agents add context over time
   - Build user profile automatically

3. **Proactive Features**
   - Agents suggest actions
   - "You have a meeting in 30 minutes"

4. **Entity Memory**
   - Track relationships automatically
   - "María is Juan's sister, lives in Barcelona, likes padel"

5. **Cross-Crew Learning**
   - LTM shared across all crews
   - "User always plays padel on Saturdays"

---

## Conclusion

This refactoring plan migrates VitaeRules from a **monolithic orchestrator** to a **CrewAI-first architecture** with:

✅ **Specialized crews** for each domain  
✅ **Shared memory** for context awareness  
✅ **Agent collaboration** via delegation  
✅ **Unified search** across all data sources  
✅ **Autonomous ChatAgent** with search  
✅ **Thin orchestrator** for simple routing

**Strategy:** Incremental, non-breaking, test-driven  
**Timeline:** 30 days (7 phases)  
**Result:** Cleaner, more extensible, more intelligent system

Ready to implement! 🚀
