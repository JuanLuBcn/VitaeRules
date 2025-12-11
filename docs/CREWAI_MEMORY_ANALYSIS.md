# CrewAI Memory Features Analysis

## Current State: **NOT USING CrewAI Memory** ❌

### What We Found

**Current Implementation:**
```python
# In query_planner.py, composer.py, etc.
Agent(
    role="Query Planner",
    goal="...",
    backstory="...",
    llm=llm,
    verbose=True,
    allow_delegation=False,
    # ❌ NO memory parameter!
)
```

**Our Custom Memory:**
```python
# We built our own memory system
class MemoryService:
    def __init__(self):
        self.stm = ShortTermMemory()  # Chat history (SQLite)
        self.ltm = LongTermMemory()   # Vector store (ChromaDB)
```

---

## CrewAI's Native Memory Features

CrewAI offers **3 types of memory** that can be passed to agents:

### 1. **Short-Term Memory**
```python
from crewai import Agent, Crew
from crewai.memory import ShortTermMemory

# CrewAI's built-in short-term memory
crew = Crew(
    agents=[agent1, agent2],
    tasks=[task1, task2],
    memory=True,  # Enables all memory types
    # OR specific:
    short_term_memory=ShortTermMemory(
        storage_path="./memory/short_term"
    )
)
```

**Features:**
- Stores conversation context during crew execution
- Shared across all agents in the crew
- Persists to disk between runs
- Automatically managed by CrewAI

### 2. **Long-Term Memory**
```python
from crewai.memory import LongTermMemory

crew = Crew(
    agents=[agent1, agent2],
    tasks=[task1, task2],
    long_term_memory=LongTermMemory(
        storage_path="./memory/long_term"
    )
)
```

**Features:**
- Stores learnings across multiple crew executions
- Uses vector embeddings for semantic search
- Agents can recall past experiences
- Builds up knowledge over time

### 3. **Entity Memory**
```python
from crewai.memory import EntityMemory

crew = Crew(
    agents=[agent1, agent2],
    tasks=[task1, task2],
    entity_memory=EntityMemory(
        storage_path="./memory/entities"
    )
)
```

**Features:**
- Tracks entities (people, places, things)
- Maintains relationships between entities
- Agents know about entities mentioned in past conversations

---

## Why We're NOT Using It (Currently)

### Our Custom Memory System:

```
app/memory/
├── short_term.py    ← Our own STM (chat history)
├── long_term.py     ← Our own LTM (ChromaDB)
└── api.py           ← MemoryService orchestrator
```

**Differences:**

| Feature | Our Custom | CrewAI Native |
|---------|-----------|---------------|
| **Storage** | SQLite + ChromaDB | CrewAI manages storage |
| **Scope** | Application-wide (all chats) | Per-crew execution |
| **Access** | Direct access via MemoryService | Through crew context |
| **Persistence** | Custom (MemoryItem model) | CrewAI format |
| **Control** | Full control | Managed by CrewAI |

**Our system is MORE FLEXIBLE** because:
- ✅ Works across different crews
- ✅ Not tied to CrewAI's execution model
- ✅ Custom data models (MemoryItem, sections, etc.)
- ✅ Direct access from orchestrator

---

## The Problem: Context Between Agents

### Current Issue:

```
User: "El partido de padel del 29/10 en club Laietà"
  ↓
Orchestrator → MemoryAgent
  ↓
MemoryAgent stores in our custom LongTermMemory
  ↓
User: "¿Dónde es el partido del 29/10?"
  ↓
Orchestrator → SearchAgent
  ↓
SearchAgent searches our custom LongTermMemory
  ↓
BUT: No shared context between these two calls!
```

**The agents are stateless!** Each call starts fresh.

### What CrewAI Memory Would Give Us:

```python
# With CrewAI memory enabled
crew = Crew(
    agents=[memory_agent, search_agent, chat_agent],
    tasks=[...],
    memory=True  # ← Magic! Shared context
)

# Agents automatically share:
- What was discussed
- What actions were taken
- What entities were mentioned
```

**BUT:** Our architecture doesn't use Crew for orchestration - we have a **custom orchestrator**!

---

## Solution Options

### Option 1: Keep Custom Memory + Add Context Management ⭐ RECOMMENDED

**What to do:**
Add conversation context to our orchestrator:

```python
class Orchestrator:
    def __init__(self, memory_service):
        self.memory = memory_service
        self.contexts = {}  # Per-chat context
    
    async def handle_message(self, message, chat_id, user_id):
        # Get or create context for this chat
        context = self.contexts.get(chat_id, {
            "recent_intents": [],
            "recent_entities": {},
            "conversation_summary": ""
        })
        
        # Detect intent
        intent = await self._detect_intent(message)
        
        # Pass context to agent
        result = await self._route_to_agent(
            intent, 
            message, 
            user_id,
            context=context  # ← Share context!
        )
        
        # Update context
        context["recent_intents"].append(intent)
        context["recent_entities"].update(result.get("entities", {}))
        self.contexts[chat_id] = context
```

**Pros:**
- ✅ Keeps our flexible custom memory
- ✅ Adds context sharing
- ✅ Works with our architecture
- ✅ No CrewAI dependency for orchestration

**Cons:**
- ⚠️ We manage context ourselves

---

### Option 2: Use CrewAI Memory for Agent Execution

**What to do:**
Use CrewAI's Crew with memory INSIDE each agent:

```python
class MemoryAgent:
    def __init__(self, memory_service):
        self.memory = memory_service
    
    async def store(self, message: str, user_id: str):
        # Create a mini-crew with memory
        agent = Agent(
            role="Memory Storer",
            goal="Store information",
            llm=llm
        )
        
        crew = Crew(
            agents=[agent],
            tasks=[...],
            memory=True  # ← CrewAI handles context
        )
        
        result = crew.kickoff()
        
        # Also store in our LTM
        await self.memory.store_memory(result)
```

**Pros:**
- ✅ Automatic context within agent execution
- ✅ Best of both worlds

**Cons:**
- ⚠️ More complex (two memory systems)
- ⚠️ Crew overhead for single-agent calls

---

### Option 3: Hybrid - CrewAI for Multi-Agent, Custom for Storage

**What to do:**
- Use CrewAI memory when **multiple agents collaborate**
- Use custom memory for **data persistence**

**Example:**
```python
# Multi-step task with collaboration
crew = Crew(
    agents=[analyzer, enricher, storer],
    tasks=[analyze_task, enrich_task, store_task],
    memory=True  # ← Agents share context during this flow
)

result = crew.kickoff(inputs={"message": user_message})

# Then persist to our custom LTM
await memory_service.store_memory(result)
```

**Pros:**
- ✅ Best of both worlds
- ✅ Agents collaborate smartly
- ✅ Data stored in our format

**Cons:**
- ⚠️ Two memory systems to manage

---

## My Recommendation for Our Architecture

**Option 1: Custom Context Management** ⭐

**Why:**
1. We're NOT using Crew for orchestration (we have custom orchestrator)
2. Our memory system is already excellent
3. We just need to **pass context between agents**

**Implementation:**

```python
# In orchestrator
class Orchestrator:
    async def handle_message(self, message, chat_id, user_id):
        # Build context from recent history
        context = await self._build_context(chat_id, user_id)
        
        # Detect intent
        intent = await self._detect_intent(message, context)
        
        # Route to agent WITH context
        result = await self._route_to_agent(
            intent, 
            message, 
            user_id,
            context  # ← Key!
        )
        
        return result

class MemoryAgent:
    async def store(self, message: str, user_id: str, context: dict):
        """Store with awareness of recent conversation."""
        
        # Use context to enrich
        entities = context.get("recent_entities", {})
        
        # Store
        await self.memory.store(...)

class SearchAgent:
    async def search(self, query: str, user_id: str, context: dict):
        """Search with awareness of what was just discussed."""
        
        # Expand query with context
        if context.get("recent_entities"):
            enhanced_query = f"{query} {context['recent_entities']}"
        
        # Search
        results = await self.memory.search(enhanced_query)
```

---

## Conclusion

**We DON'T need CrewAI's memory because:**
1. ❌ We don't use Crew for orchestration (custom orchestrator)
2. ❌ Our memory system is more flexible
3. ✅ We just need to **pass context between agents**

**What we SHOULD do:**
✅ Add conversation context management to orchestrator
✅ Pass context to agents when routing
✅ Agents use context to make smarter decisions

**We already have the memory infrastructure!** We just need to wire the context passing.

---

## Action Items

1. [ ] Add `context` parameter to all agent methods
2. [ ] Orchestrator builds context from recent chat history
3. [ ] Orchestrator passes context when routing
4. [ ] Agents use context to enrich their understanding
5. [ ] Update context after each agent call

This gives us all the benefits of shared memory WITHOUT depending on CrewAI's execution model! 🎯
