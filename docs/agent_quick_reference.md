# Agent Architecture Quick Reference

## System Flow

```
User Message
    ↓
IntentClassifier → (intent, confidence)
    ↓
[confidence < 0.7?] → Ask clarification
    ↓
Route to Agent (List/Task/Note/Query)
    ↓
Agent.handle() → AgentResult
    ↓
[needs_confirmation?] → Show preview, wait for yes/no
    ↓
[confirmed?] → Agent.execute_confirmed()
    ↓
Response to User
```

## Intents

| Intent | Examples | Agent | Confirmation? |
|--------|----------|-------|---------------|
| `LIST` | "Add milk to list", "What's on shopping list?" | ListAgent | Yes (add), No (query) |
| `TASK` | "Remind me to call John", "What are my tasks?" | TaskAgent | Yes (create), No (query) |
| `NOTE` | "Remember that John likes coffee" | NoteAgent | Yes |
| `QUERY` | "What did I do yesterday?", "Tell me about..." | QueryAgent | No (read-only) |
| `UNKNOWN` | Unclear message | None | Ask clarification |

## Agent Methods

### All Agents Implement

```python
class MyAgent(BaseAgent):
    async def can_handle(self, message: str) -> tuple[bool, float]:
        """Check if message belongs to this agent."""
        # Return (can_handle, confidence)
    
    async def handle(
        self, message: str, chat_id: str, user_id: str, context: dict | None
    ) -> AgentResult:
        """Process message, return result."""
        # Extract data
        # Return AgentResult(needs_confirmation=True/False)
    
    async def execute_confirmed(self, data: dict) -> AgentResult:
        """Execute after user confirms."""
        # Only needed if agent uses confirmation
```

### AgentResult Structure

```python
@dataclass
class AgentResult:
    success: bool              # Did operation succeed?
    message: str               # Response to show user
    data: dict | None          # Data to store for confirmation
    needs_confirmation: bool   # Should we ask user to confirm?
    preview: str | None        # What will happen if user confirms
    error: str | None          # Error details if failed
```

## Common Patterns

### Pattern 1: Simple Read-Only Agent (Query)

```python
async def handle(self, message, chat_id, user_id, context):
    result = await self.retrieval_crew.process_query(message)
    return AgentResult(
        success=True,
        message=result["answer"],
        needs_confirmation=False  # Read-only, no confirmation
    )
```

### Pattern 2: Confirmation-Based Agent (List, Task, Note)

```python
async def handle(self, message, chat_id, user_id, context):
    # Extract data
    data = self._extract_data(message)
    
    # Return preview
    return AgentResult(
        success=True,
        message=f"Preview: {data}",
        needs_confirmation=True,
        preview=f"Will save: {data}",
        data={"extracted": data, "chat_id": chat_id}
    )

async def execute_confirmed(self, data):
    # Actually save/create
    await self.tool.execute(data["extracted"])
    return AgentResult(
        success=True,
        message="✅ Done!",
        needs_confirmation=False
    )
```

### Pattern 3: Multi-Operation Agent (List)

```python
async def handle(self, message, chat_id, user_id, context):
    operation = self._detect_operation(message)  # add/query/remove
    
    if operation == "query":
        return await self._handle_query(...)  # No confirmation
    elif operation == "add":
        return await self._handle_add(...)    # With confirmation
    elif operation == "remove":
        return await self._handle_remove(...) # With confirmation
```

## LLM Extraction Pattern

All agents use LLM for data extraction with fallback:

```python
def _extract_data(self, message: str) -> dict:
    """Extract structured data using LLM."""
    prompt = f"""Extract data from: "{message}"
    
    Return JSON:
    {{
        "field1": "value1",
        "field2": ["item1", "item2"]
    }}
    
    Examples:
    - Input → Output
    """
    
    try:
        # Use LLM
        result = self.llm.generate_json(
            prompt=prompt,
            system_prompt="Return ONLY valid JSON."
        )
        return result
    except Exception as e:
        # Fallback to regex
        return self._parse_with_regex(message)
```

## Orchestrator Usage

### Basic Usage

```python
from app.agents.orchestrator import AgentOrchestrator

orchestrator = AgentOrchestrator(llm_service, memory_service)

result = await orchestrator.handle_message(
    message="Add milk to shopping list",
    chat_id="123",
    user_id="user1"
)

print(result["message"])
print(result["needs_confirmation"])
```

### With Confirmation

```python
# First message
result = await orchestrator.handle_message(
    message="Add milk to shopping list",
    chat_id="123",
    user_id="user1"
)

if result["needs_confirmation"]:
    # Show preview to user
    print(result["message"])
    
    # User says "yes"
    confirm_result = await orchestrator.handle_message(
        message="yes",
        chat_id="123",
        user_id="user1"
    )
    
    print(confirm_result["message"])  # "✅ Done!"
```

### Low Confidence

```python
result = await orchestrator.handle_message(
    message="uhm something",  # Unclear
    chat_id="123",
    user_id="user1"
)

# Returns clarification message
print(result["message"])
# "I'm not sure what you want me to do. Did you want to:
#  • Save a note?
#  • Create a task?
#  ..."
```

## Adding New Agent - Checklist

- [ ] Add intent to `IntentType` enum
- [ ] Update `IntentClassifier` prompt with examples
- [ ] Create `YourAgent` class extending `BaseAgent`
- [ ] Implement `can_handle()` method
- [ ] Implement `handle()` method
- [ ] Implement `execute_confirmed()` if using confirmation
- [ ] Add extraction logic (LLM + fallback)
- [ ] Register agent in `AgentOrchestrator`
- [ ] Export from `__init__.py`
- [ ] Write tests
- [ ] Update documentation

## Testing

### Test Individual Agent

```python
from app.agents import ListAgent
from app.llm import LLMService
from app.memory import MemoryService

llm = LLMService()
memory = MemoryService()
agent = ListAgent(llm, memory)

result = await agent.handle(
    "Add milk to shopping list",
    chat_id="test",
    user_id="test"
)

assert result.success
assert result.needs_confirmation
print(result.preview)
```

### Test Orchestrator

```python
from app.agents.orchestrator import AgentOrchestrator

orchestrator = AgentOrchestrator(llm, memory)

result = await orchestrator.handle_message(
    "Add milk to shopping list",
    chat_id="test",
    user_id="test"
)

assert result["needs_confirmation"]
```

### Run Full Test Suite

```bash
python scripts/test_agent_architecture.py
```

## Confidence Thresholds

| Confidence | Action |
|------------|--------|
| 0.9 - 1.0 | High - Execute directly |
| 0.7 - 0.9 | Medium - Execute but log |
| 0.5 - 0.7 | Low - Ask clarification |
| 0.0 - 0.5 | Very low - Definitely ask |

Currently using 0.7 as threshold in orchestrator.

## Error Handling

### Agent Level

```python
async def handle(self, message, chat_id, user_id, context):
    try:
        # Process message
        result = await self.tool.execute(...)
        return AgentResult(success=True, message="Done!")
    except Exception as e:
        logger.error(f"Agent failed: {e}")
        return AgentResult(
            success=False,
            message="Sorry, something went wrong.",
            error=str(e)
        )
```

### Orchestrator Level

```python
result = await orchestrator.handle_message(...)

if not result.get("success"):
    error = result.get("error", "Unknown error")
    logger.error(f"Operation failed: {error}")
    await send_message("Sorry, couldn't complete that.")
```

## Common Tasks

### Get User's Lists

```python
from app.agents import ListAgent

agent = ListAgent(llm, memory)
result = await agent.handle(
    "What are my lists?",
    chat_id="123",
    user_id="user1"
)
print(result.message)
```

### Create Task

```python
from app.agents import TaskAgent

agent = TaskAgent(llm, memory)
result = await agent.handle(
    "Remind me to call John tomorrow",
    chat_id="123",
    user_id="user1"
)

if result.needs_confirmation:
    # Show preview
    print(result.preview)
    
    # Confirm
    confirm = await agent.execute_confirmed(result.data)
    print(confirm.message)
```

### Save Memory

```python
from app.agents import NoteAgent

agent = NoteAgent(llm, memory)
result = await agent.handle(
    "Remember that John likes coffee",
    chat_id="123",
    user_id="user1"
)

# Confirm and save
confirm = await agent.execute_confirmed(result.data)
```

### Ask Question

```python
from app.agents import QueryAgent

agent = QueryAgent(llm, memory)
result = await agent.handle(
    "What did I save about John?",
    chat_id="123",
    user_id="user1"
)

print(result.message)  # Answer with sources
```

## File Structure

```
src/app/agents/
├── __init__.py              # Exports
├── base.py                  # BaseAgent, AgentResult
├── intent_classifier.py     # IntentClassifier, IntentType
├── list_agent.py            # List management
├── task_agent.py            # Task management
├── note_agent.py            # Memory/note saving
├── query_agent.py           # Question answering
└── orchestrator.py          # Main coordinator

scripts/
└── test_agent_architecture.py  # Full test suite

docs/
├── migration_guide.md       # Old → New migration
└── agent_quick_reference.md # This file
```

## Key Principles

1. **Single Responsibility**: Each agent handles one domain
2. **LLM-First**: Use LLM for extraction, regex as fallback
3. **Confirmation**: Preview before destructive actions
4. **Error Handling**: Graceful degradation, helpful messages
5. **Extensibility**: Easy to add new agents
6. **Testability**: Each agent independently testable

## Performance Tips

- **Cache classifier results** for similar messages
- **Batch LLM calls** when possible
- **Use async** for all I/O operations
- **Log confidence scores** to tune thresholds
- **Monitor agent selection** to detect misclassifications

## Debug Tips

### Check Classification

```python
intent, confidence = await classifier.classify(message)
print(f"Intent: {intent}, Confidence: {confidence}")
```

### Check Agent Selection

```python
for intent_type, agent in orchestrator.agents.items():
    can_handle, conf = await agent.can_handle(message)
    print(f"{intent_type}: {can_handle} ({conf})")
```

### Trace Full Flow

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# All agents log their actions
result = await orchestrator.handle_message(...)
```

## Resources

- **Main Documentation**: `docs/migration_guide.md`
- **Test Examples**: `scripts/test_agent_architecture.py`
- **Code Examples**: `src/app/agents/orchestrator.py`
- **Agent Examples**: All files in `src/app/agents/`

---

**Last Updated**: 2024
**Version**: 1.0 (New Architecture)
