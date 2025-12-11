# Agent Architecture & Context Sharing

## Current Architecture: Tools vs Agents

### **Important Distinction:**

In the current implementation, we have **TWO types of components**:

1. **Tools** (TaskTool, ListTool) - **STATELESS**, no LLM, just database operations
2. **Crews** (RetrievalCrew) - Has LLM, but also **STATELESS**

**Neither of them maintain context or have access to conversation state.**

---

## Current Design: Orchestrator Owns ALL Context

```
┌─────────────────────────────────────────────────────┐
│         ConversationalOrchestrator                  │
│                                                     │
│  • Owns conversation context (self.contexts)       │
│  • Makes ALL LLM decisions                         │
│  • Asks questions to user                          │
│  • Decides when to execute tools                   │
│  • Manages multi-turn conversations                │
└──────────────┬──────────────────────────────────────┘
               │
               │ Uses as stateless tools
               │
    ┌──────────┼──────────┬──────────────┐
    ▼          ▼          ▼              ▼
┌─────────┐ ┌─────────┐ ┌────────┐ ┌──────────────┐
│TaskTool │ │ListTool │ │Memory  │ │RetrievalCrew │
│         │ │         │ │Service │ │              │
│ NO LLM  │ │ NO LLM  │ │ NO LLM │ │ HAS LLM      │
│ NO CTX  │ │ NO CTX  │ │ NO CTX │ │ NO CTX       │
│         │ │         │ │        │ │              │
│ Just DB │ │ Just DB │ │ Just DB│ │ Just Search  │
└─────────┘ └─────────┘ └────────┘ └──────────────┘
```

### What This Means:

**Tools CANNOT:**
- ❌ Access conversation context
- ❌ Ask questions to the user
- ❌ Make LLM decisions
- ❌ Know what was said before
- ❌ Share state with each other

**Tools CAN:**
- ✅ Execute database operations (CRUD)
- ✅ Return success/error results
- ✅ Be called by orchestrator
- ✅ Validate input data

---

## Your Questions Answered

### Q1: "Do different agents share context?"

**Answer: NO - Because there ARE NO AGENTS in the traditional sense.**

We have:
- **1 Orchestrator** (has context, has LLM, talks to user)
- **4 Tools** (no context, no LLM, just operations)

Only the **Orchestrator** has context. Tools are stateless functions.

```python
# Orchestrator has context
self.contexts = {
    "chat_123": {
        "last_message": "Recuérdame llamar a Juan",
        "last_reply": "¿Cuándo?",
        "waiting_for_more": True
    }
}

# Tools have NO context
class TaskTool:
    def create_task(self, user_id, title, due_at, ...):
        # Just creates task in DB
        # No idea about conversation
        # No access to what user said before
        pass
```

---

### Q2: "Can a tool ask the orchestrator to ask the user for more information?"

**Answer: NO - Current design doesn't support this.**

But we have **THREE possible approaches** depending on what you want:

---

## Approach 1: Current Design (LLM Asks Everything)

**How it works:**
- LLM in orchestrator asks ALL questions upfront
- Only calls tool when it has complete data
- Tool receives complete, validated data
- Tool never needs to ask for more

```
User: "Recuérdame llamar a Juan"
  ↓
Orchestrator LLM: "Need WHEN"
  ↓
Orchestrator asks: "¿Cuándo quieres que te lo recuerde?"
  ↓
User: "Mañana a las 10"
  ↓
Orchestrator LLM: "Now I have everything"
  ↓
Calls tool: create_task(title="llamar a Juan", due_at="mañana 10:00")
  ↓
Tool: Just creates task (no questions needed)
```

**Pros:**
- ✅ Simple tool implementation
- ✅ Tools are pure functions (no state)
- ✅ Single source of truth (orchestrator)
- ✅ Easy to test tools

**Cons:**
- ❌ LLM must know ALL business rules
- ❌ If tool validation fails, need to re-prompt
- ❌ Tools can't have domain-specific question logic

---

## Approach 2: Tools Return "NeedMoreInfo" Signals

**How it works:**
- Tool attempts operation with provided data
- If data is incomplete/invalid, returns special error
- Orchestrator catches error and asks user
- Repeats until tool succeeds

```python
# Modified tool
class TaskTool:
    def create_task(self, user_id, title, due_at=None, ...):
        # Validate
        if not due_at:
            raise MissingFieldError(
                field="due_at",
                message="¿Cuándo quieres que te lo recuerde?"
            )
        
        # Create task
        ...

# Modified orchestrator
async def _execute_tool_call(self, tool_call, ...):
    try:
        result = await tool.execute(...)
        return {"success": True, "result": result}
    
    except MissingFieldError as e:
        # Tool needs more info!
        # Save context with what we have so far
        self.contexts[chat_id] = {
            "tool_call": tool_call,
            "missing_field": e.field,
            "waiting_for": e.field
        }
        
        # Ask user
        return {
            "message": e.message,
            "waiting_for_input": True
        }
```

**Flow Example:**
```
User: "Recuérdame llamar a Juan"
  ↓
LLM returns: create_task(title="llamar a Juan")
  ↓
Orchestrator calls tool
  ↓
Tool: "Missing due_at!" → raises MissingFieldError
  ↓
Orchestrator catches error
  ↓
Orchestrator asks: "¿Cuándo quieres que te lo recuerde?"
  ↓
User: "Mañana a las 10"
  ↓
Orchestrator calls tool again: create_task(..., due_at="mañana 10:00")
  ↓
Tool: Success! ✅
```

**Pros:**
- ✅ Tools enforce their own validation
- ✅ Business logic stays in tools
- ✅ Can have domain-specific questions
- ✅ LLM doesn't need to know all rules

**Cons:**
- ❌ More complex error handling
- ❌ Need to save partial tool_call state
- ❌ Tools become more complex
- ❌ May call tool multiple times (retry loop)

---

## Approach 3: Tools as Conversational Agents (Multi-Agent)

**How it works:**
- Each "tool" becomes a full agent with LLM
- Agent manages its own conversation sub-flow
- Orchestrator delegates to agent
- Agent returns when done or needs help

```python
class TaskAgent:
    def __init__(self, llm_service):
        self.llm = llm_service
        self.context = {}
    
    async def handle(self, user_id, initial_data, ask_user_callback):
        """
        Handle task creation with multi-turn conversation.
        
        Args:
            ask_user_callback: Function to ask user questions
        """
        # Check what we have
        if not initial_data.get("due_at"):
            # Ask user via callback
            answer = await ask_user_callback("¿Cuándo quieres que te lo recuerde?")
            initial_data["due_at"] = self._parse_date(answer)
        
        # Create task
        task = self._create_task(**initial_data)
        return {"success": True, "task": task}

# Orchestrator delegates
async def _execute_tool_call(self, tool_call, ...):
    if tool_call["name"] == "create_task":
        agent = self.task_agent
        
        # Give agent a callback to ask questions
        result = await agent.handle(
            user_id=user_id,
            initial_data=tool_call["args"],
            ask_user_callback=self._ask_user_and_wait
        )
        
        return result
```

**Pros:**
- ✅ Each domain owns its conversation logic
- ✅ Can have complex multi-turn flows per domain
- ✅ Domain experts can design question flows
- ✅ Very flexible

**Cons:**
- ❌ Much more complex architecture
- ❌ Multiple LLM calls (expensive, slow)
- ❌ Context management becomes complicated
- ❌ User sees multiple "personalities"
- ❌ This is what we MOVED AWAY FROM! 😅

---

## Recommendation: Hybrid (Approach 1 + Approach 2)

### **Best of Both Worlds:**

1. **LLM asks for common fields** (Approach 1)
   - When/Where/Who questions handled by orchestrator
   - Natural conversation flow
   - Fast for 90% of cases

2. **Tools validate and signal if special cases** (Approach 2)
   - Tool-specific validations (e.g., "due date must be in future")
   - Business rule violations
   - Edge cases LLM doesn't know about

### Implementation:

```python
# Custom exception for tools
class ToolValidationError(Exception):
    """Raised when tool needs more info from user."""
    def __init__(self, field: str, question: str, current_data: dict):
        self.field = field
        self.question = question
        self.current_data = current_data
        super().__init__(question)

# Tool with validation
class TaskTool:
    def create_task(self, user_id, title, due_at=None, description=None, ...):
        """Create task with validation."""
        
        # REQUIRED field validation
        if not title or len(title.strip()) < 3:
            raise ToolValidationError(
                field="title",
                question="El título es muy corto. ¿Puedes darme más detalles?",
                current_data={"due_at": due_at}
            )
        
        # BUSINESS RULE validation
        if due_at:
            parsed_date = self._parse_date(due_at)
            if parsed_date < datetime.now():
                raise ToolValidationError(
                    field="due_at",
                    question="Esa fecha ya pasó. ¿Cuándo quieres el recordatorio?",
                    current_data={"title": title, "description": description}
                )
        
        # All good, create task
        task_id = str(uuid4())
        # ... DB insert
        return {"id": task_id, "title": title, "due_at": due_at}

# Orchestrator handles tool errors
async def _execute_tool_call(self, tool_call, media_ref, user_id):
    """Execute tool with validation error handling."""
    
    tool_name = tool_call.get("name")
    args = tool_call.get("args", {})
    
    try:
        # Try to execute
        if tool_name == "create_task":
            result = await self._tool_create_task(user_id, args)
            return result
        
        # ... other tools
    
    except ToolValidationError as e:
        # Tool needs more info!
        self.tracer.info(
            "tool_validation_failed",
            extra={"field": e.field, "tool": tool_name}
        )
        
        # Save what we have so far
        self.contexts[chat_id] = {
            "tool_call": tool_call,  # Original call
            "current_data": e.current_data,  # What we have
            "missing_field": e.field,  # What we need
            "retry_count": 0
        }
        
        # Re-raise to let caller handle
        raise  # Orchestrator will ask user
    
    except Exception as e:
        # Other errors
        self.tracer.error(f"Tool execution failed: {e}")
        raise

# Modified _handle_new_request to catch validation errors
async def _handle_new_request(self, message, media_ref, chat_id, user_id):
    """Handle new request with validation error handling."""
    
    analysis = await self._analyze_message(message, media_ref)
    reply = analysis.get("reply", "No entendí bien.")
    tool_call = analysis.get("tool_call")
    
    if tool_call and tool_call.get("name"):
        try:
            # Try to execute
            await self._execute_tool_call(tool_call, media_ref, user_id)
            
            # Success!
            self.contexts.pop(chat_id, None)
            return {"message": reply, "waiting_for_input": False}
        
        except ToolValidationError as e:
            # Tool needs more info
            # Context already saved by _execute_tool_call
            return {
                "message": e.question,  # Tool's question
                "waiting_for_input": True
            }
        
        except Exception as e:
            # Other errors
            return {
                "message": f"{reply}\n\n(Error: {str(e)})",
                "waiting_for_input": False
            }
    
    else:
        # LLM asking question
        self.contexts[chat_id] = {
            "last_message": message,
            "last_reply": reply,
            "waiting_for_more": True
        }
        return {"message": reply, "waiting_for_input": True}

# Modified _handle_answer to retry tool calls
async def _handle_answer(self, answer, media_ref, context, chat_id, user_id):
    """Handle answer with tool retry logic."""
    
    # Check if we're retrying a tool call
    if "tool_call" in context:
        # User answered tool's question
        # Update the args with new field
        tool_call = context["tool_call"]
        missing_field = context["missing_field"]
        
        # Merge current_data with new answer
        # Let LLM parse the answer
        parse_prompt = f"""
Usuario respondió: "{answer}"
Campo que falta: {missing_field}

Extrae el valor para {missing_field}.
JSON: {{"value": "..."}}
"""
        parsed = self.llm.generate_json(parse_prompt, "Extract field value")
        
        # Update tool_call args
        tool_call["args"][missing_field] = parsed.get("value")
        
        # Retry tool execution
        try:
            await self._execute_tool_call(tool_call, media_ref, user_id)
            
            # Success!
            self.contexts.pop(chat_id, None)
            return {
                "message": "✅ Listo!",
                "waiting_for_input": False
            }
        
        except ToolValidationError as e:
            # Still missing something or invalid
            # Max retries check
            retry_count = context.get("retry_count", 0) + 1
            if retry_count > 3:
                self.contexts.pop(chat_id, None)
                return {
                    "message": "Lo siento, no pude completar eso. Intenta de nuevo.",
                    "waiting_for_input": False
                }
            
            # Update context and ask again
            context["retry_count"] = retry_count
            context["current_data"] = e.current_data
            context["missing_field"] = e.field
            
            return {
                "message": e.question,
                "waiting_for_input": True
            }
    
    else:
        # Normal conversation flow (LLM asking questions)
        last_reply = context.get("last_reply", "")
        combined = f"[Antes: {last_reply}]\nUsuario: {answer}"
        
        analysis = await self._analyze_message(combined, media_ref)
        reply = analysis.get("reply")
        tool_call = analysis.get("tool_call")
        
        if tool_call:
            # Try execution (may raise ToolValidationError)
            try:
                await self._execute_tool_call(tool_call, media_ref, user_id)
                self.contexts.pop(chat_id, None)
                return {"message": reply, "waiting_for_input": False}
            
            except ToolValidationError as e:
                # Tool validation failed
                return {"message": e.question, "waiting_for_input": True}
        
        else:
            # LLM still asking
            context["last_message"] = answer
            context["last_reply"] = reply
            return {"message": reply, "waiting_for_input": True}
```

---

## Flow Example: Hybrid Approach

### Scenario: User creates task with past date

```
Turn 1:
User: "Recuérdame llamar a Juan ayer"
  ↓
LLM analyzes: Has title + due_at
  ↓
LLM returns:
{
  "reply": "Te recordaré ayer llamar a Juan",
  "tool_call": {
    "name": "create_task",
    "args": {"title": "llamar a Juan", "due_at": "ayer"}
  }
}
  ↓
Orchestrator calls create_task(title="llamar a Juan", due_at="ayer")
  ↓
TaskTool validates:
  - Parses "ayer" → yesterday's date
  - Checks: yesterday < today → INVALID!
  ↓
TaskTool raises:
  ToolValidationError(
    field="due_at",
    question="Esa fecha ya pasó. ¿Cuándo quieres el recordatorio?",
    current_data={"title": "llamar a Juan"}
  )
  ↓
Orchestrator catches error
  ↓
Orchestrator saves context:
{
  "tool_call": {...},
  "current_data": {"title": "llamar a Juan"},
  "missing_field": "due_at",
  "retry_count": 0
}
  ↓
Bot → User: "Esa fecha ya pasó. ¿Cuándo quieres el recordatorio?"

Turn 2:
User: "Mañana a las 3pm"
  ↓
Orchestrator sees context has "tool_call" → retry mode
  ↓
Parses "mañana a las 3pm" → updates tool_call.args["due_at"]
  ↓
Retries: create_task(title="llamar a Juan", due_at="mañana 3pm")
  ↓
TaskTool validates: tomorrow > today → VALID! ✅
  ↓
TaskTool creates task
  ↓
Orchestrator clears context
  ↓
Bot → User: "✅ Listo!"
```

---

## Comparison Table

| Feature | Approach 1 (Current) | Approach 2 (Tools Signal) | Approach 3 (Multi-Agent) | Hybrid (1+2) |
|---------|---------------------|--------------------------|-------------------------|--------------|
| **Complexity** | Low | Medium | High | Medium |
| **LLM Calls** | 1-2 per conversation | 1-2 per conversation | 3-5+ per conversation | 1-2 per conversation |
| **Tool Simplicity** | Very simple (DB only) | Medium (validation logic) | Complex (has LLM) | Medium (validation) |
| **Business Rules** | In LLM prompt | In tool code | In agent code | Split (common in LLM, special in tools) |
| **Error Handling** | LLM must predict | Tool validates & signals | Agent handles internally | Tool validates, orchestrator handles |
| **Testability** | Easy (pure functions) | Medium (test validations) | Hard (mock conversations) | Medium (test validations) |
| **User Experience** | Fast, natural | Fast, natural | Slower, may feel fragmented | Fast, natural |
| **Maintenance** | Easy | Medium | Hard | Medium |
| **When Tool Changes** | Update LLM prompt | Just update tool | Update agent logic | Just update tool |

---

## My Recommendation: **Hybrid Approach**

### Why?

1. **90% of cases handled by LLM** (fast, natural)
   - "Recuérdame llamar a Juan" → LLM asks "¿Cuándo?"
   - User answers → LLM calls tool with complete data
   - Tool succeeds ✅

2. **10% edge cases handled by tools** (correct, robust)
   - User gives past date → Tool catches it
   - Tool asks user to fix
   - Orchestrator retries
   - Tool succeeds ✅

3. **Best of both worlds:**
   - ✅ Natural conversation (LLM)
   - ✅ Robust validation (Tools)
   - ✅ Simple architecture (not multi-agent)
   - ✅ Easy to test (validation is in code)
   - ✅ Easy to extend (add new validations to tools)

---

## Implementation Steps (If You Want Hybrid)

### Step 1: Create ToolValidationError
```python
# src/app/exceptions.py
class ToolValidationError(Exception):
    """Raised when tool needs more info from user."""
    def __init__(self, field: str, question: str, current_data: dict = None):
        self.field = field
        self.question = question
        self.current_data = current_data or {}
        super().__init__(question)
```

### Step 2: Update Tools with Validation
```python
# src/app/tools/task_tool.py
from app.exceptions import ToolValidationError

class TaskTool:
    def create_task(self, user_id, title, due_at=None, ...):
        # Validate title
        if not title or len(title.strip()) < 3:
            raise ToolValidationError(
                field="title",
                question="El título es muy corto. ¿Puedes darme más detalles sobre la tarea?",
                current_data={"due_at": due_at}
            )
        
        # Validate due_at if provided
        if due_at:
            parsed = self._parse_date(due_at)
            if parsed < datetime.now():
                raise ToolValidationError(
                    field="due_at",
                    question="Esa fecha ya pasó. ¿Cuándo quieres el recordatorio?",
                    current_data={"title": title}
                )
        
        # Create task
        ...
```

### Step 3: Update Orchestrator to Handle Tool Errors
(See code examples above)

---

## Decision Time! 🤔

**What do you prefer?**

**Option A: Keep current design (Approach 1)**
- LLM handles ALL question logic
- Tools are pure DB operations
- Simpler, but LLM must know all rules

**Option B: Implement Hybrid (Approach 1 + 2)**
- LLM handles common questions
- Tools validate and signal errors
- More robust, tools enforce business rules

**Option C: Full Multi-Agent (Approach 3)**
- Each domain is an agent
- Complex but very flexible
- (We moved away from this, but we can go back)

Let me know and I'll implement whichever you choose! 🚀
