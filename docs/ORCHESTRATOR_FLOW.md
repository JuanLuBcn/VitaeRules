# Conversational Orchestrator Flow

## Overview
The orchestrator is the **single bot personality** that handles all conversations using an LLM-driven approach with tool calling.

---

## Main Entry Point: `handle_message()`

```
┌─────────────────────────────────────────┐
│  User sends message via Telegram        │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  Extract media reference (if any)       │
│  Clean message text                     │
└─────────────┬───────────────────────────┘
              │
              ▼
         Check context
              │
      ┌───────┴───────┐
      ▼               ▼
 Has context?    No context
 (mid-convo)     (new request)
      │               │
      │               │
      ▼               ▼
_handle_answer()  _handle_new_request()
```

---

## Flow 1: New Request (`_handle_new_request()`)

```
┌──────────────────────────────────────────────┐
│  1. Call _analyze_message()                  │
│     - Send message to LLM                    │
│     - LLM analyzes intent                    │
│     - LLM generates natural reply            │
│     - LLM optionally returns tool_call       │
└──────────────┬───────────────────────────────┘
               │
               ▼
       LLM returns: {
         "reply": "...",
         "tool_call": {...} or null
       }
               │
        ┌──────┴──────┐
        ▼             ▼
   Has tool_call?   No tool_call
        │             │
        │             │
        ▼             ▼
┌─────────────┐  ┌──────────────────────┐
│ Execute     │  │ Save context:        │
│ tool        │  │ - last_message       │
│             │  │ - last_reply         │
└──────┬──────┘  │ - waiting_for_more   │
       │         └──────┬───────────────┘
       │                │
       ▼                ▼
┌─────────────┐  ┌──────────────────────┐
│ Clear       │  │ Return reply         │
│ context     │  │ waiting_for_input:   │
│             │  │ TRUE                 │
└──────┬──────┘  └──────────────────────┘
       │
       ▼
┌─────────────┐
│ Return      │
│ reply       │
│ waiting:    │
│ FALSE       │
└─────────────┘
```

### Example: Complete Task (1-turn)
```
User: "Recuérdame llamar a mi madre mañana a las 10"
  ↓
LLM analyzes → Infers: TASK with all info
  ↓
LLM returns:
{
  "reply": "Perfecto! Te recordaré mañana a las 10 📞",
  "tool_call": {
    "name": "create_task",
    "args": {
      "title": "llamar a mi madre",
      "due_at": "mañana 10:00"
    }
  }
}
  ↓
Orchestrator executes create_task()
  ↓
Bot: "Perfecto! Te recordaré mañana a las 10 📞"
[DONE - 1 turn]
```

### Example: Incomplete Task (needs question)
```
User: "Recuérdame llamar a Juan"
  ↓
LLM analyzes → Infers: TASK but missing WHEN
  ↓
LLM returns:
{
  "reply": "Claro! ¿Cuándo quieres que te lo recuerde?",
  "tool_call": null
}
  ↓
Orchestrator saves context:
{
  "last_message": "Recuérdame llamar a Juan",
  "last_reply": "Claro! ¿Cuándo quieres que te lo recuerde?",
  "waiting_for_more": true
}
  ↓
Bot: "Claro! ¿Cuándo quieres que te lo recuerde?"
[WAITING for user answer]
```

---

## Flow 2: Handling Answer (`_handle_answer()`)

```
┌──────────────────────────────────────────────┐
│  User answers previous question              │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│  1. Retrieve saved context                   │
│     - last_message (original request)        │
│     - last_reply (what we asked)             │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│  2. Combine context + new answer             │
│     "[Antes pregunté: ...]                   │
│      Usuario responde: ..."                  │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│  3. Call _analyze_message() with context     │
│     LLM sees full conversation               │
│     LLM decides: more questions or execute   │
└──────────────┬───────────────────────────────┘
               │
               ▼
       LLM returns: {
         "reply": "...",
         "tool_call": {...} or null
       }
               │
        ┌──────┴──────┐
        ▼             ▼
   Has tool_call?   No tool_call
   (ready!)         (needs more)
        │             │
        │             │
        ▼             ▼
┌─────────────┐  ┌──────────────────────┐
│ Execute     │  │ Update context:      │
│ tool        │  │ - last_message       │
│             │  │ - last_reply         │
└──────┬──────┘  └──────┬───────────────┘
       │                │
       ▼                ▼
┌─────────────┐  ┌──────────────────────┐
│ Clear       │  │ Return reply         │
│ context     │  │ waiting_for_input:   │
│ DONE!       │  │ TRUE (continue)      │
└──────┬──────┘  └──────────────────────┘
       │
       ▼
┌─────────────┐
│ Return      │
│ reply       │
│ waiting:    │
│ FALSE       │
└─────────────┘
```

### Example: Answer Completes Task
```
[Context from before]:
{
  "last_message": "Recuérdame llamar a Juan",
  "last_reply": "Claro! ¿Cuándo quieres que te lo recuerde?",
  "waiting_for_more": true
}

User: "Mañana a las 10"
  ↓
Orchestrator combines:
"[Antes pregunté: Claro! ¿Cuándo quieres que te lo recuerde?]
 Usuario responde: Mañana a las 10"
  ↓
LLM analyzes → Now has all info (who: Juan, when: mañana 10:00)
  ↓
LLM returns:
{
  "reply": "Perfecto! Te recordaré mañana a las 10",
  "tool_call": {
    "name": "create_task",
    "args": {
      "title": "llamar a Juan",
      "due_at": "mañana 10:00"
    }
  }
}
  ↓
Orchestrator executes create_task()
  ↓
Orchestrator clears context (conversation done)
  ↓
Bot: "Perfecto! Te recordaré mañana a las 10"
[DONE - 2 turns total]
```

---

## Flow 3: Tool Execution (`_execute_tool_call()`)

```
┌──────────────────────────────────────────────┐
│  LLM returned tool_call:                     │
│  {                                           │
│    "name": "create_task",                    │
│    "args": {...}                             │
│  }                                           │
└──────────────┬───────────────────────────────┘
               │
               ▼
       Route by tool name
               │
    ┌──────────┼──────────┬──────────┐
    ▼          ▼          ▼          ▼
create_task  save_note  add_to_list  search_memory
    │          │          │          │
    ▼          ▼          ▼          ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ Call    │ │ Call    │ │ Call    │ │ Call    │
│ TaskTool│ │ Memory  │ │ ListTool│ │ Retrieval│
│         │ │ Service │ │         │ │ Crew    │
└────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
     │           │           │           │
     └───────────┴───────────┴───────────┘
                 │
                 ▼
         Return success/error
```

### Available Tools:

**1. `create_task`**
- Args: title, description, due_at, people, tags, media_path
- Calls: `TaskTool.create_task()`
- Returns: `{success: true, task_id: ...}`

**2. `save_note`**
- Args: content, people, tags, media_path, media_type
- Calls: `MemoryService.store_memory()`
- Returns: `{success: true}`

**3. `add_to_list`**
- Args: list_name, items
- Calls: `ListTool.add_item()`
- Returns: `{success: true, list_name: ..., items: [...]}`

**4. `search_memory`**
- Args: query
- Calls: `RetrievalCrew.search()`
- Returns: `{success: true, results: [...]}`

---

## Flow 4: LLM Analysis (`_analyze_message()`)

```
┌──────────────────────────────────────────────┐
│  Construct prompt for LLM:                   │
│                                              │
│  1. User message                             │
│  2. Media context (if any)                   │
│  3. Instructions (analyze, ask, act)         │
│  4. Tool descriptions                        │
│  5. Response format (JSON)                   │
│  6. Examples                                 │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│  Call LLM (qwen3:1.7b via Ollama)           │
│  - System: "Asistente conversacional..."     │
│  - Prompt: Full instructions + examples      │
│  - Format: JSON                              │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│  LLM Decision Tree:                          │
│                                              │
│  1. ANALYZE what user wants                  │
│     - Task? Note? List? Search?              │
│                                              │
│  2. CHECK if info is complete                │
│     - Task: Has WHEN? Has WHAT?              │
│     - List: Has WHERE (list name)?           │
│     - Note: Has CONTENT?                     │
│                                              │
│  3. IF missing info → ASK                    │
│     - "¿Cuándo?" (for tasks)                 │
│     - "¿A qué lista?" (for lists)            │
│     - "¿Con quién?" (if people involved)     │
│     - tool_call = null                       │
│                                              │
│  4. IF complete → ACT                        │
│     - Generate natural confirmation          │
│     - tool_call = {name: ..., args: {...}}   │
└──────────────┬───────────────────────────────┘
               │
               ▼
       Return JSON:
       {
         "reply": "Natural Spanish response",
         "tool_call": {
           "name": "create_task",
           "args": {...}
         } OR null
       }
```

### Prompt Structure:

```python
prompt = f"""Usuario: "{message}"{media_context}

Eres un asistente personal. Tu trabajo:

1. ANALIZA qué quiere el usuario (tarea, nota, lista, búsqueda)
2. Si falta contexto PREGUNTA naturalmente:
   - ¿CUÁNDO? (para tareas/recordatorios)
   - ¿CON QUIÉN? (si involucra personas)
   - ¿DÓNDE? (para listas: compra, trabajo, etc)
   - Nunca preguntes "¿qué quieres hacer?" - ya lo sabes por contexto

3. Después de 1-2 preguntas, ACTÚA:
   - create_task: recordatorios/tareas futuras
   - save_note: información para recordar
   - add_to_list: listas (compra, trabajo, etc)
   - search_memory: buscar algo guardado

JSON: {{"reply": "...", "tool_call": {{...}} OR null}}

[Examples...]
"""

system = """Asistente conversacional en español.
Haz preguntas contextuales (cuándo/dónde/con quién).
Después de 1-2 respuestas, ejecuta la acción.
JSON válido, sin markdown."""
```

### Key Principles:
- **Infer intent** - Don't ask "what do you want?"
- **Ask contextually** - When? Where? Who? (based on situation)
- **Be brief** - Max 1-2 questions before executing
- **Natural language** - Generate all text (no templates)

---

## Context Management

### Context Structure:
```python
contexts = {
  chat_id: {
    "last_message": "Recuérdame llamar a Juan",
    "last_reply": "¿Cuándo quieres que te lo recuerde?",
    "waiting_for_more": True
  }
}
```

### Context Lifecycle:

```
New Request
   ↓
No context (fresh start)
   ↓
Analyze message
   ↓
IF needs more info:
  - Save context
  - waiting_for_input = True
   ↓
User answers
   ↓
Has context (retrieve)
   ↓
Analyze with context
   ↓
IF ready to execute:
  - Execute tool
  - Clear context ← IMPORTANT!
  - waiting_for_input = False
```

### Why Clear Context?
- Each conversation is independent
- No state leakage between requests
- Next message starts fresh
- Simple mental model for user

---

## Complete Example Flow

### Scenario: User wants to create a task but gives incomplete info

```
┌─────────────────────────────────────────────────────┐
│ Turn 1: User sends message                          │
└────────────┬────────────────────────────────────────┘
             │
             ▼
User: "Recuérdame llamar a Juan"
             │
             ▼
┌────────────────────────────────────────────────────┐
│ Orchestrator.handle_message()                      │
│ - No context → _handle_new_request()               │
└────────────┬───────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────┐
│ _analyze_message()                                 │
│ LLM sees: "Recuérdame llamar a Juan"               │
│ LLM thinks:                                        │
│   - Intent: TASK                                   │
│   - What: "llamar a Juan" ✓                        │
│   - When: MISSING ✗                                │
│   → Need to ask!                                   │
└────────────┬───────────────────────────────────────┘
             │
             ▼
LLM returns:
{
  "reply": "Claro! ¿Cuándo quieres que te lo recuerde?",
  "tool_call": null
}
             │
             ▼
┌────────────────────────────────────────────────────┐
│ _handle_new_request() processes response           │
│ - tool_call is null → needs more info              │
│ - Save context:                                    │
│   {                                                │
│     "last_message": "Recuérdame llamar a Juan",    │
│     "last_reply": "Claro! ¿Cuándo...",             │
│     "waiting_for_more": true                       │
│   }                                                │
└────────────┬───────────────────────────────────────┘
             │
             ▼
Bot → User: "Claro! ¿Cuándo quieres que te lo recuerde?"
             │
             │
┌────────────┴────────────────────────────────────────┐
│ Turn 2: User answers                                │
└────────────┬────────────────────────────────────────┘
             │
             ▼
User: "Mañana a las 10"
             │
             ▼
┌────────────────────────────────────────────────────┐
│ Orchestrator.handle_message()                      │
│ - Has context → _handle_answer()                   │
└────────────┬───────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────┐
│ _handle_answer()                                   │
│ - Retrieve context                                 │
│ - Combine:                                         │
│   "[Antes pregunté: Claro! ¿Cuándo...]            │
│    Usuario responde: Mañana a las 10"             │
└────────────┬───────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────┐
│ _analyze_message() with combined context           │
│ LLM sees full conversation                         │
│ LLM thinks:                                        │
│   - Intent: TASK                                   │
│   - What: "llamar a Juan" ✓                        │
│   - When: "mañana a las 10" ✓                      │
│   → All info complete, execute!                    │
└────────────┬───────────────────────────────────────┘
             │
             ▼
LLM returns:
{
  "reply": "Perfecto! Te recordaré mañana a las 10",
  "tool_call": {
    "name": "create_task",
    "args": {
      "title": "llamar a Juan",
      "due_at": "mañana 10:00"
    }
  }
}
             │
             ▼
┌────────────────────────────────────────────────────┐
│ _handle_answer() processes response                │
│ - tool_call exists → execute                       │
└────────────┬───────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────┐
│ _execute_tool_call()                               │
│ - Route to _tool_create_task()                     │
│ - Call TaskTool.create_task(...)                   │
│ - Returns: {success: true, task_id: 123}           │
└────────────┬───────────────────────────────────────┘
             │
             ▼
┌────────────────────────────────────────────────────┐
│ _handle_answer() after execution                   │
│ - Clear context (conversation done)                │
│ - Return:                                          │
│   {                                                │
│     "message": "Perfecto! Te recordaré...",        │
│     "waiting_for_input": False                     │
│   }                                                │
└────────────┬───────────────────────────────────────┘
             │
             ▼
Bot → User: "Perfecto! Te recordaré mañana a las 10"

┌────────────────────────────────────────────────────┐
│ DONE! Task created, context cleared                │
│ Next message starts fresh                          │
└────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

### 1. **Single Personality**
- Orchestrator IS the bot
- No separate intent classifier
- No separate enrichment agent
- One consistent voice

### 2. **LLM-Driven Conversation**
- LLM generates all responses
- LLM decides when to ask vs execute
- LLM formats tool calls
- No templates (except deprecated code)

### 3. **Minimal Context**
- Only last 2 turns (last_message + last_reply)
- Cleared after tool execution
- No long conversation history
- Works with small 1.7B model

### 4. **Natural Questioning**
- Ask When/Where/Who based on context
- Never ask "what do you want to do?"
- Max 1-2 questions before executing
- Infer intent from user's words

### 5. **Tool Calling Pattern**
- LLM returns: `{"reply": "...", "tool_call": {...} or null}`
- Orchestrator executes when LLM ready
- Clean separation: LLM decides, orchestrator executes
- Fallback if tool fails: show error but keep reply

---

## State Diagram

```
                    START
                      │
                      ▼
              New Message Arrives
                      │
                      ▼
              Extract Media (if any)
                      │
                      ▼
            Check for Saved Context
                      │
              ┌───────┴────────┐
              ▼                ▼
         No Context        Has Context
         (New Req)         (Answer)
              │                │
              ▼                │
      _handle_new_request()    │
              │                │
              ▼                │
      _analyze_message()       │
              │                │
              ▼                │
      LLM Decision             │
              │                │
      ┌───────┴────────┐       │
      ▼                ▼       │
  tool_call?      No tool      │
      │                │       │
      ▼                ▼       │
   Execute         Save        │
   Tool            Context ────┘
      │                │
      ▼                ▼
  Clear          Return Reply
  Context        (waiting=true)
      │
      ▼
  Return Reply
  (waiting=false)
      │
      ▼
    DONE

[Next message starts fresh if context was cleared]
[Next message continues conversation if context saved]
```

---

## Error Handling

### JSON Parsing Errors
```python
try:
    result = self.llm.generate_json(prompt, system_prompt)
    if "reply" not in result:
        result["reply"] = "Lo siento, no entendí bien."
    if "tool_call" not in result:
        result["tool_call"] = None
    return result
except Exception as e:
    return {
        "reply": "Perdón, tuve un problema. ¿Puedes repetir?",
        "tool_call": None
    }
```

### Tool Execution Errors
```python
try:
    result = await self._execute_tool_call(tool_call, media_ref, user_id)
    return {"message": reply, "waiting_for_input": False}
except Exception as e:
    return {
        "message": f"{reply}\n\n(Error: {str(e)})",
        "waiting_for_input": False
    }
```

### Graceful Degradation
- If LLM fails → Ask user to repeat
- If tool fails → Show error but keep LLM's message
- If JSON invalid → Use defaults (reply + no tool_call)
- Never crash, always respond

---

## Performance Considerations

### For 1.7B Model (qwen3:1.7b):
- ✅ Lean prompts (~200 tokens)
- ✅ Minimal context (2 turns max)
- ✅ Clear examples in prompt
- ✅ Simple JSON format
- ⚠️ May struggle with complex tool calls
- ⚠️ May need prompt refinement

### Latency:
- 1 LLM call per turn (new request)
- 1 LLM call per turn (answer)
- Tool execution ~50-200ms
- Total: ~1-3 seconds per interaction

### Fallback Strategy:
If qwen3:1.7b struggles with tool calling:
- **Option B**: LLM generates text only, orchestrator handles logic
- Keep natural conversation
- Simpler for small model
- Still feels natural to user
