# Architecture Refactor: Conversational Orchestrator

## What Changed

### Old Architecture (Agent-Based Microservices)
```
User Message
  ↓
Telegram Adapter
  ↓
Orchestrator (Router)
  ↓ IntentClassifier.classify()
  ↓ Routes to specialized agent
TaskAgent/ListAgent/NoteAgent (Conversational)
  ↓ Returns AgentResponse(needs_enrichment=True)
  ↓
EnrichmentAgent (Multi-turn Q&A)
  ↓ Asks follow-up questions
  ↓ Extracts answers
  ↓
Back to TaskAgent
  ↓ Saves via Tool
  ↓
Response to user
```

**Problems:**
- Too many handoffs, complex state management
- Multiple "personalities" (each agent talks differently)
- 3-5 LLM calls per request (slow!)
- Enrichment felt robotic (form-filling)
- Hard to debug (who's responsible?)

---

### New Architecture (Conversational Orchestrator)
```
User Message
  ↓
Telegram Adapter
  ↓
ConversationalOrchestrator (THE BOT)
  │
  ├─ analyze_message() [1 LLM call]
  │   → Understands intent + extracts entities
  │
  ├─ If unclear: Ask user to clarify
  ├─ If missing info: Ask naturally
  ├─ If complete: Show understanding → Confirm
  │
  └─ User confirms → Execute via tools:
      ├─ TaskTool.create_task()
      ├─ ListTool.add_items()
      ├─ MemoryService.store_memory()
      └─ RetrievalCrew.search()
```

**Advantages:**
- ✅ Single personality (Orchestrator IS the bot)
- ✅ 1 LLM call per turn (faster!)
- ✅ Natural conversation (not form-filling)
- ✅ User confirmation (not dual LLM verification)
- ✅ Simple state (last 2 turns only)
- ✅ Easy to debug (one flow)

---

## Key Design Principles

### 1. **Orchestrator IS the Conversational Partner**
```python
# User talks to Orchestrator
# Orchestrator uses tools internally
# User never sees "TaskAgent" or "ListAgent"
```

### 2. **Agents Become Stateless Tools**
```python
# OLD: Agent handles conversation
class TaskAgent:
    async def handle(self, message, chat_id, user_id):
        # Extract, converse, enrich, save
        ...

# NEW: Agent is just a function
class TaskTool:
    def create_task(self, user_id, title, due_at=None, ...):
        # Just save to DB
        return task
```

### 3. **Minimal Context for Small Model**
```python
# Only remember last exchange
self.contexts[chat_id] = {
    "action_type": "task",
    "entities": {"title": "llamar a madre"},
    "waiting_for": "due_at",
    "last_question": "¿Cuándo?"
}

# NOT full conversation history (model too small)
```

### 4. **User Confirmation > Dual LLM Verification**
```python
# OLD: Two LLM calls to verify
intent1 = orchestrator.guess_intent()
intent2 = intent_classifier.verify_intent()

# NEW: One LLM, user confirms
Bot: "✅ Crear tarea: Llamar a madre. ¿Correcto?"
User: "Sí"
```

### 5. **Template Questions (No LLM)**
```python
# OLD: Generate question with LLM
question = await llm.generate(f"Ask about {field}")

# NEW: Pre-written templates (instant!)
questions = {
    "task": {"due_at": "¿Cuándo quieres que te lo recuerde?"},
    ...
}
```

---

## Conversation Flow Examples

### Example 1: Complete Message (1 turn)
```
User: "Recuérdame llamar a mi madre mañana a las 10"

Orchestrator:
  → analyze_message()
  → Extracts: {action: task, title: "llamar a mi madre", due_at: "mañana 10:00"}
  → Has all info
  → Shows preview

Bot: "✅ Crear tarea: Llamar a mi madre
     📅 Cuándo: mañana a las 10
     
     ¿Correcto?"

User: "Sí"

Orchestrator:
  → create_task()
  
Bot: "✅ Tarea creada: Llamar a mi madre"
```

### Example 2: Missing Info (3 turns)
```
User: "Recuérdame llamar a mi madre"

Orchestrator:
  → analyze_message()
  → Extracts: {action: task, title: "llamar a mi madre"}
  → Missing: due_at
  → Ask naturally

Bot: "¿Cuándo quieres que te lo recuerde?"

User: "Mañana a las 10"

Orchestrator:
  → extract_field_value("mañana a las 10", field="due_at")
  → Now complete
  → Show preview

Bot: "✅ Crear tarea: Llamar a mi madre
     📅 Cuándo: mañana a las 10
     
     ¿Correcto?"

User: "Sí"

Bot: "✅ Tarea creada"
```

### Example 3: Unclear Intent (2 turns)
```
User: "Leche"

Orchestrator:
  → analyze_message()
  → confidence: 0.4 (too low)
  → Ask for clarification

Bot: "No estoy seguro. ¿Quieres crear una tarea, guardar una nota, añadir a una lista, o buscar algo?"

User: "Añadir a mi lista"

Orchestrator:
  → Now clear: action=list, items=["leche"]
  → Show preview

Bot: "📝 Añadir a Compras:
       • leche
     
     ¿Correcto?"

User: "Sí"

Bot: "✅ Añadido a Compras"
```

### Example 4: User Correction (3 turns)
```
User: "Guardar que Juan le gusta el café"

Orchestrator:
  → analyze_message()
  → Extracts: {action: note, content: "Juan le gusta el café"}
  → Show preview

Bot: "💾 Guardar nota: Juan le gusta el café
     
     ¿Correcto?"

User: "No, quiero una tarea para comprarle café"

Orchestrator:
  → User said "no" → clear context
  → Treat as new request
  → analyze_message("quiero una tarea para comprarle café")
  → Extracts: {action: task, title: "comprarle café a Juan"}

Bot: "✅ Crear tarea: Comprarle café a Juan
     
     ¿Correcto?"

User: "Sí"

Bot: "✅ Tarea creada"
```

---

## LLM Prompts (Lean for 1.7B Model)

### Analysis Prompt (Main Intelligence)
```
Usuario dice: "{message}"

¿Qué quiere hacer?

Opciones:
- task: Hacer algo en el futuro (recordatorio, tarea)
- note: Guardar información o memoria
- list: Añadir/quitar de lista
- query: Buscar información guardada

Extrae toda la info disponible.

JSON:
{
  "action_type": "task|note|list|query",
  "confidence": 0.0-1.0,
  "entities": {}
}
```

**System Prompt:**
```
Analiza y extrae. JSON válido, sin markdown.

Ejemplos:
"Recuérdame llamar a Juan" → {"action_type": "task", ...}
"Juan le gusta café" → {"action_type": "note", ...}
"Añade leche" → {"action_type": "list", ...}
"¿Qué hice ayer?" → {"action_type": "query", ...}
```

**Why this works:**
- Short (~150 tokens)
- Clear options (4 types)
- Few-shot examples
- Structured output (JSON)
- One task (analyze)

---

## Components Status

### ✅ Active Components

**ConversationalOrchestrator** (`orchestrator_v2.py`)
- Main bot personality
- Conversation flow manager
- Uses tools to execute actions

**Tools** (Stateless DB operations)
- `TaskTool` - Create/query tasks
- `ListTool` - Manage lists
- `MemoryService` - Store/retrieve notes
- `RetrievalCrew` - Search memories

**Telegram Adapter**
- Thin wrapper
- Just passes messages to Orchestrator
- Sends responses back

### ❌ Deprecated Components

**IntentClassifier** (`intent_classifier.py`)
- No longer used (Orchestrator analyzes directly)
- Kept for reference only

**EnrichmentAgent** (`enrichment_agent.py`)
- Replaced by natural conversation in Orchestrator
- No separate enrichment phase

**Old Agent Classes**
- `TaskAgent.handle()` - Replaced by `TaskTool.create_task()`
- `ListAgent.handle()` - Replaced by `ListTool` operations
- `NoteAgent.handle()` - Replaced by `MemoryService.store_memory()`

**AgentResponse / AgentResult**
- No longer needed (Orchestrator returns simple dicts)

---

## Migration Path

### Phase 1: Test New Orchestrator
1. Keep old orchestrator as `orchestrator_old.py`
2. Use `orchestrator_v2.py` in Telegram adapter
3. Test with real users
4. Compare behavior

### Phase 2: Simplify Agents
1. Remove conversation logic from agents
2. Make them pure functions (tools)
3. Remove AgentResponse, needs_enrichment

### Phase 3: Clean Up
1. Archive old components
2. Update documentation
3. Remove unused code

---

## Performance Expectations

### Old Architecture
- **LLM calls per request**: 3-5
- **Average latency**: 10-25 seconds
- **State complexity**: High (multiple agents)
- **Debug difficulty**: Hard (many components)

### New Architecture
- **LLM calls per request**: 1-2
- **Average latency**: 3-8 seconds
- **State complexity**: Low (single context dict)
- **Debug difficulty**: Easy (one flow)

---

## Next Steps

1. ✅ Create `ConversationalOrchestrator`
2. ⏳ Update Telegram adapter to use it
3. ⏳ Test conversation flow
4. ⏳ Refine prompts based on results
5. ⏳ Simplify agent classes to pure tools
6. ⏳ Archive deprecated components
7. ⏳ Update documentation

---

## Testing Checklist

### Basic Flows
- [ ] Complete task: "Recuérdame llamar a Juan mañana"
- [ ] Incomplete task: "Recuérdame algo" → Bot asks what
- [ ] Complete note: "Juan le gusta el café"
- [ ] Complete list: "Añade leche a compras"
- [ ] Unclear message: "Leche" → Bot asks intent

### Multi-turn
- [ ] Task + missing when: "Llamar a Juan" → "¿Cuándo?" → "Mañana"
- [ ] List + missing name: "Añade leche" → "¿A qué lista?" → "Compras"
- [ ] User correction: Show preview → "No, es X" → Restart

### Confirmation
- [ ] User says "sí" → Execute
- [ ] User says "no" → Ask to rephrase
- [ ] User unclear → Ask again

### Edge Cases
- [ ] Very long message
- [ ] Message with media
- [ ] Rapid consecutive messages
- [ ] Context timeout (old conversation)
