# Option A: LLM-Driven Conversation with Tool Calling

## What Changed

### Before (Robotic):
```
User: "Recuérdame llamar a mi madre"
Bot: (Analyzes) → (Extracts to JSON) → (Checks missing fields)
Bot: "¿Cuándo quieres que te lo recuerde?" [Template]
User: "Mañana"
Bot: (Extracts) → (Shows preview) → "✅ Crear tarea: Llamar a mi madre. ¿Correcto?"
User: "Sí"
Bot: "✅ Tarea creada"
```

**Problems:**
- Template responses (not natural)
- Forced confirmation ("¿Correcto?")
- Multi-step: analyze → ask → extract → confirm → execute
- Feels like filling a form

### After (Natural):
```
User: "Recuérdame llamar a mi madre"
Bot: (LLM generates) "Claro! ¿Cuándo quieres que te lo recuerde?"
User: "Mañana"
Bot: (LLM decides) "Perfecto! Te recordaré llamar a tu madre mañana"
     → Calls create_task(title="llamar a mi madre", due_at="mañana")
```

**Advantages:**
- Natural conversation (LLM generates responses)
- LLM decides when to execute
- No forced confirmations
- Feels like talking to a person

---

## How It Works

### The Prompt (Option A):

```python
"""Usuario: "{message}"

Eres un asistente personal amigable. Ayudas a crear tareas, guardar notas, gestionar listas y buscar información.

Herramientas disponibles:
- create_task: Crear recordatorio/tarea (args: title, due_at, people)
- save_note: Guardar información (args: content, people)
- add_to_list: Añadir a lista (args: list_name, items)
- search_memory: Buscar info guardada (args: query)

RESPONDE al usuario:
- Si entiendes qué quiere: responde y llama la herramienta
- Si falta info: pregunta naturalmente
- Habla español, sé amigable y conciso

JSON:
{
  "reply": "Tu respuesta al usuario",
  "tool_call": {"name": "create_task", "args": {"title": "...", "due_at": "..."}} OR null
}
"""
```

### LLM Response Format:

```json
{
  "reply": "Perfecto! Te recordaré llamar a Juan mañana",
  "tool_call": {
    "name": "create_task",
    "args": {
      "title": "llamar a Juan",
      "due_at": "mañana"
    }
  }
}
```

**OR** if needs more info:

```json
{
  "reply": "Claro! ¿Cuándo quieres que te lo recuerde?",
  "tool_call": null
}
```

---

## Flow Examples

### Example 1: Complete Information
```
User: "Recuérdame llamar a Juan mañana a las 10"

LLM Response:
{
  "reply": "Perfecto! Te recordaré llamar a Juan mañana a las 10",
  "tool_call": {
    "name": "create_task",
    "args": {"title": "llamar a Juan", "due_at": "mañana a las 10"}
  }
}

Orchestrator:
→ Sends reply to user
→ Executes create_task()
→ Done (1 turn!)
```

### Example 2: Missing Information
```
User: "Recuérdame llamar a Juan"

LLM Response:
{
  "reply": "Claro! ¿Cuándo quieres que te lo recuerde?",
  "tool_call": null
}

Orchestrator:
→ Sends reply to user
→ Waits for answer

User: "Mañana a las 10"

LLM Response (with context):
{
  "reply": "Perfecto! Te recordaré mañana a las 10",
  "tool_call": {
    "name": "create_task",
    "args": {"title": "llamar a Juan", "due_at": "mañana a las 10"}
  }
}

Orchestrator:
→ Sends reply
→ Executes create_task()
→ Done (2 turns)
```

### Example 3: Note
```
User: "Guarda que a Juan le gusta el café"

LLM Response:
{
  "reply": "Perfecto! Ya sé que a Juan le gusta el café ☕",
  "tool_call": {
    "name": "save_note",
    "args": {
      "content": "A Juan le gusta el café",
      "people": ["Juan"]
    }
  }
}

Orchestrator:
→ Sends reply
→ Executes save_note()
→ Done (1 turn)
```

### Example 4: List
```
User: "Añade leche y huevos a la compra"

LLM Response:
{
  "reply": "Listo! Añadido leche y huevos a tu lista de compra 🛒",
  "tool_call": {
    "name": "add_to_list",
    "args": {
      "list_name": "compra",
      "items": ["leche", "huevos"]
    }
  }
}

Orchestrator:
→ Sends reply
→ Executes add_to_list()
→ Done (1 turn)
```

---

## Testing Plan

### ✅ Will Work If LLM Can:
1. **Generate natural Spanish responses**
   - "Perfecto! Te ayudo con eso"
   - Not just extracting JSON

2. **Decide when to call tools**
   - Has enough info → call tool
   - Missing info → ask question, tool_call=null

3. **Format JSON correctly**
   - Both "reply" and "tool_call" fields
   - Valid JSON structure

### ❌ Will Fail If LLM:
1. **Can't generate natural text** (too small)
   - Falls back to robotic responses

2. **Doesn't understand tool calling** (too small)
   - Never sets tool_call or always sets it

3. **JSON formatting errors** (common with small models)
   - Invalid JSON, missing fields

---

## Fallback Plan (Option B)

If Option A fails, we have Option B ready:

**Option B: LLM generates text, Orchestrator decides tools**

```python
# LLM only generates natural response
{
  "reply": "Perfecto! ¿Cuándo te lo recuerdo?",
  "understood": true,
  "action": "task",
  "data": {"title": "llamar a Juan"},
  "needs": ["due_at"]
}

# Orchestrator:
# - Shows LLM's natural reply
# - Checks "needs" to see if more questions
# - When needs=[], calls appropriate tool based on "action"
```

**This splits responsibilities:**
- LLM: Natural language generation (easier)
- Orchestrator: Tool calling logic (deterministic)

---

## How to Test

### Test 1: Complete Task
Send: `"Recuérdame llamar a mi madre mañana a las 10"`

**Expected:**
- Natural response (not template)
- Task created in 1 turn
- Check logs for tool_call

### Test 2: Incomplete Task
Send: `"Recuérdame llamar a Juan"`

**Expected:**
- Bot asks "¿Cuándo?" naturally
- You answer "Mañana"
- Bot creates task with natural confirmation

### Test 3: Note
Send: `"Guarda que a María le gustan las flores"`

**Expected:**
- Natural confirmation
- Note saved with people=["María"]

### Test 4: List
Send: `"Añade leche a la compra"`

**Expected:**
- Natural response
- Added to list "compra"

### What to Watch:
1. **Response naturalness** - Does it sound human?
2. **Tool calling accuracy** - Does it call tools correctly?
3. **JSON errors** - Does qwen3:1.7b format JSON correctly?
4. **Conversation flow** - Does it ask good follow-up questions?

---

## Log Analysis

After testing, check logs for:

```bash
cat data/trace.jsonl | grep "llm_response"
```

Look for:
- `has_tool_call: true` when should execute
- `has_tool_call: false` when should ask more
- `tool_name: create_task` etc.

---

## Decision Point

After 5-10 test messages:

**If it works:**
- ✅ Keep Option A
- LLM is smart enough!
- Refine prompts for better responses

**If it fails:**
- ⚠️ Switch to Option B
- Model too small for full control
- Split responsibilities (LLM text, orchestrator tools)

**Ready to test! Start the bot and try it out.**
