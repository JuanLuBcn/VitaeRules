# Migration Guide: Old System → New Agent Architecture

## Overview

This guide explains how to migrate from the complex Router → Planner → Enricher → Clarifier system to the new simplified agent-based architecture.

## Architecture Comparison

### Old System (Complex)
```
Message
  ↓
Router (ConversationIntent enum with underscores)
  ↓
Planner (IntentType enum with dots)
  ↓
Enricher
  ↓
Clarifier (if ambiguous)
  ↓
Tool Caller
  ↓
Response
```

**Issues:**
- Two separate intent detection systems (Router + Planner)
- Complex heuristics (is_question, is_list_query, etc.)
- Hard to maintain and extend
- Duplicated logic across multiple layers
- Difficult to trace bugs

### New System (Simple)
```
Message
  ↓
IntentClassifier (simple 4-way: note/task/list/query)
  ↓
Specialized Agent (self-contained)
  ↓
Response (with optional confirmation)
```

**Benefits:**
- Single intent classification
- Each agent handles its domain completely
- Easy to add new agents
- Clean separation of concerns
- Better testability
- Simpler debugging

## Components

### 1. IntentClassifier (`src/app/agents/intent_classifier.py`)

**Purpose:** Simple LLM-based classifier that routes to one of 4 intents.

**Intents:**
- `NOTE`: Save memory/fact ("Remember that...")
- `TASK`: Create/manage tasks ("Remind me to...")
- `LIST`: Add/query lists ("Add to list...")
- `QUERY`: Ask questions ("What did I...?")
- `UNKNOWN`: Can't determine (ask for clarification)

**Returns:**
- Intent type
- Confidence score (0.0-1.0)

**Usage:**
```python
classifier = IntentClassifier(llm_service)
intent, confidence = await classifier.classify("Añade mantequilla a la lista")
# Returns: (IntentType.LIST, 0.92)
```

### 2. BaseAgent (`src/app/agents/base.py`)

**Purpose:** Abstract interface all agents implement.

**Key Methods:**
- `can_handle(message)`: Check if agent can handle this message
- `handle(message, chat_id, user_id)`: Process message, return AgentResult
- `execute_confirmed(data)`: Execute after user confirms

**AgentResult:**
```python
@dataclass
class AgentResult:
    success: bool
    message: str              # Response to user
    data: dict | None         # Data for confirmation
    needs_confirmation: bool  # Ask user yes/no?
    preview: str | None       # What will be done
    error: str | None         # Error details
```

### 3. Specialized Agents

#### ListAgent (`src/app/agents/list_agent.py`)
- Handles: add, query, remove from lists
- Auto-creates lists on first add
- Parses multiple items: "apples, oranges and bananas"
- Infers list names: "compra" → "lista de la compra"
- Shows preview before adding

#### TaskAgent (`src/app/agents/task_agent.py`)
- Handles: create, complete, query tasks
- Extracts: title, due date, priority
- Uses task_tool for persistence
- Shows preview before creating

#### NoteAgent (`src/app/agents/note_agent.py`)
- Handles: saving notes and memories
- Extracts: content, people, places, tags
- Uses memory_service for persistence
- Shows preview before saving

#### QueryAgent (`src/app/agents/query_agent.py`)
- Handles: questions and retrieval
- Uses retrieval_crew (existing)
- Read-only (no confirmation needed)
- Shows sources with answer

### 4. Orchestrator (`src/app/agents/orchestrator.py`)

**Purpose:** Routes messages to agents and handles confirmations.

**Flow:**
1. Check for pending confirmation
2. Classify intent
3. Low confidence? Ask for clarification
4. Route to appropriate agent
5. Need confirmation? Store and ask user
6. Return result

**Usage:**
```python
orchestrator = AgentOrchestrator(llm_service, memory_service)

result = await orchestrator.handle_message(
    message="Añade mantequilla a la lista",
    chat_id="123",
    user_id="user1",
)

if result["needs_confirmation"]:
    # Show preview, wait for yes/no
    confirm_result = await orchestrator.handle_message(
        message="yes",
        chat_id="123",
        user_id="user1",
    )
```

## Migration Steps

### Step 1: Test New System

Run the test script to verify all agents work:

```bash
python scripts/test_agent_architecture.py
```

### Step 2: Update Telegram Adapter

Replace complex flow in `src/app/adapters/telegram.py`:

**Old code (remove):**
```python
# Router classification
intent = await self.router.classify(message)

# Planner intent detection
planner_intent = await self.planner.detect_intent(message)

# Various heuristics
if is_question(message):
    ...
if is_list_query(message):
    ...
```

**New code (add):**
```python
# Simple orchestrator
result = await self.orchestrator.handle_message(
    message=message,
    chat_id=chat_id,
    user_id=user_id,
)

if result["needs_confirmation"]:
    await self.send_message(result["message"])
    # Store pending in session
else:
    await self.send_message(result["message"])
```

### Step 3: Initialize Orchestrator

In `telegram.py` `__init__`:

```python
from app.agents.orchestrator import AgentOrchestrator

class TelegramAdapter:
    def __init__(self):
        self.llm = LLMService()
        self.memory = MemoryService()
        self.orchestrator = AgentOrchestrator(self.llm, self.memory)
```

### Step 4: Handle Confirmations

Update confirmation handling:

```python
async def handle_confirmation(self, message: str, chat_id: str, user_id: str):
    """User responded to confirmation prompt."""
    result = await self.orchestrator.handle_message(
        message=message,
        chat_id=chat_id,
        user_id=user_id,
    )
    await self.send_message(result["message"])
```

### Step 5: Test in Production

1. Deploy with feature flag to switch between old/new system
2. Test with real users
3. Monitor errors and edge cases
4. Iterate if needed

### Step 6: Remove Old Code

Once confident new system works:

1. Delete `src/app/llm/router.py`
2. Delete `src/app/crews/capture/planner.py`
3. Delete heuristic functions (is_question, is_list_query, etc.)
4. Remove old intent enums
5. Clean up unused imports

## Testing Scenarios

Test these cases to verify migration:

### Lists
- ✅ "Añade mantequilla a la lista de la compra"
- ✅ "Berenjenas, tomates y aguacates"
- ✅ "Qué hay en la lista?"
- ✅ Multiple items with "y", "and", commas

### Tasks
- ✅ "Remind me to call John tomorrow"
- ✅ "I need to finish report by Friday"
- ✅ "What are my tasks?"
- ✅ "Mark laundry as done"

### Notes
- ✅ "Remember that John likes coffee"
- ✅ "Note: Meeting went well"
- ✅ "Barcelona is beautiful"

### Queries
- ✅ "What did I do yesterday?"
- ✅ "Tell me about John"
- ✅ "When is the deadline?"

### Edge Cases
- ✅ Ambiguous messages (low confidence)
- ✅ Confirmation flow (yes/no)
- ✅ Multiple pending confirmations
- ✅ Unknown intents

## Benefits of New System

### For Users
- Faster responses (less processing layers)
- Clearer previews before actions
- Better error messages
- More accurate intent detection

### For Developers
- Easier to understand code flow
- Simple to add new agents (just implement BaseAgent)
- Better testability (each agent independent)
- Clear separation of concerns
- Less heuristic logic
- Fewer bugs from cascading complexity

### For Maintenance
- Single source of truth for intents
- No duplicate logic
- Clear error traces
- Easy to debug (check agent directly)
- Better logging

## Adding New Agents

To add a new agent type (e.g., EventAgent for calendar):

1. **Add to IntentType enum:**
```python
class IntentType(Enum):
    EVENT = "event"  # New
    NOTE = "note"
    TASK = "task"
    LIST = "list"
    QUERY = "query"
```

2. **Update classifier prompt:**
Add examples for new intent type in `intent_classifier.py`.

3. **Create new agent:**
```python
class EventAgent(BaseAgent):
    async def handle(self, message, chat_id, user_id):
        # Extract event details
        # Return AgentResult
```

4. **Register in orchestrator:**
```python
self.agents = {
    IntentType.EVENT: EventAgent(llm, memory),  # New
    IntentType.LIST: ListAgent(llm, memory),
    ...
}
```

5. **Test:**
```python
# Test event agent
result = await orchestrator.handle_message(
    "Schedule meeting with John on Friday at 3pm",
    chat_id="123",
    user_id="user1",
)
```

That's it! No need to modify Router, Planner, or other layers.

## Rollback Plan

If issues arise:

1. Keep old code until new system proven
2. Use feature flag to switch systems
3. Monitor error rates
4. Compare response quality
5. Rollback if needed

## Support

Questions or issues? Check:
- Test script: `scripts/test_agent_architecture.py`
- Example orchestrator: `src/app/agents/orchestrator.py`
- Individual agent tests in `/scripts/`

## Timeline

Recommended migration timeline:

- Week 1: Test new system thoroughly
- Week 2: Deploy with feature flag (10% traffic)
- Week 3: Increase to 50% traffic
- Week 4: 100% traffic, monitor closely
- Week 5: Remove old code if stable

## Conclusion

The new agent-based architecture is:
- **Simpler**: One classifier, specialized agents
- **Cleaner**: Clear separation, no duplicate logic
- **Extensible**: Easy to add new agents
- **Maintainable**: Better tests, easier debugging
- **Faster**: Fewer processing layers

Good luck with the migration! 🚀
