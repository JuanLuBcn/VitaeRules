# Natural Conversation Flow - Refined Prompt

## Key Changes

### ❌ OLD: Exposed tool mechanics
```
"¿Quieres crear una tarea, guardar una nota, o añadir a una lista?"
```

### ✅ NEW: Natural contextual questions
```
"¿Cuándo quieres que te lo recuerde?"
"¿A qué lista lo añado?"
"¿Con quién es?"
```

---

## The New Prompt Strategy

### 1. **Infer Intent from Context**
The LLM should understand what the user wants WITHOUT asking directly:

- "Recuérdame..." → Obviously wants a task
- "Guarda que..." → Obviously wants to save info (note)
- "Añade leche" → Obviously wants to add to a list
- "¿Qué hice ayer?" → Obviously wants to search

**Never ask**: "¿Qué quieres hacer?" - The LLM should know!

### 2. **Ask Contextual Questions**
When info is missing, ask relevant questions:

**For Tasks:**
- ¿CUÁNDO? → "¿Cuándo quieres que te lo recuerde?"
- ¿CON QUIÉN? → "¿Con quién es la reunión?"

**For Lists:**
- ¿DÓNDE? → "¿A qué lista lo añado?"

**For Notes:**
- Usually complete → Just save
- If unclear → "¿Algo más que deba saber?"

### 3. **Execute After 1-2 Questions**
Don't interrogate the user! After max 2 questions, have enough info to act.

```
Turn 1: User gives partial info
Turn 2: Bot asks 1 question
Turn 3: User answers
Turn 4: Bot executes ✅
```

### 4. **Clear Context After Tool Call**
Once a tool is called, conversation is DONE. Next message starts fresh.

---

## Expected Conversation Flows

### Flow 1: Immediate Execution (Complete Info)
```
User: "Recuérdame llamar a mi madre mañana a las 10"

Bot: "Perfecto! Te recordaré mañana a las 10 📞"
     → Calls create_task(title="llamar a mi madre", due_at="mañana 10:00")
     → Context cleared

[DONE in 1 turn]
```

### Flow 2: One Question (Missing When)
```
User: "Recuérdame llamar a Juan"

Bot: "Claro! ¿Cuándo quieres que te lo recuerde?"
     → No tool call (needs more info)

User: "Mañana a las 9"

Bot: "Perfecto! Te recordaré mañana a las 9"
     → Calls create_task(title="llamar a Juan", due_at="mañana 9:00")
     → Context cleared

[DONE in 2 turns]
```

### Flow 3: Ambiguous Input (Needs Clarification)
```
User: "Leche"

Bot: "¿A qué lista lo añado?"
     → No tool call (needs list name)

User: "A la compra"

Bot: "Listo! Leche en tu lista de compra 🛒"
     → Calls add_to_list(list_name="compra", items=["leche"])
     → Context cleared

[DONE in 2 turns]
```

### Flow 4: Note (Usually Immediate)
```
User: "Guarda que a María le gustan las flores"

Bot: "Anotado! María le gustan las flores 🌸"
     → Calls save_note(content="A María le gustan las flores", people=["María"])
     → Context cleared

[DONE in 1 turn]
```

### Flow 5: Search
```
User: "¿Qué hice ayer?"

Bot: "Déjame buscar... [resultados]"
     → Calls search_memory(query="qué hice ayer")
     → Context cleared

[DONE in 1 turn]
```

---

## What LLM Should Learn

### ✅ DO:
1. **Infer intent from context** - Don't ask what they want
2. **Ask WHEN for tasks** - "¿Cuándo?" not "¿Qué tipo de tarea?"
3. **Ask WHERE for lists** - "¿A qué lista?" not "¿Quieres una lista?"
4. **Be brief** - Max 1-2 questions before executing
5. **Use emojis** - 📞 🛒 🌸 ✅ (makes it friendly)

### ❌ DON'T:
1. **Don't ask about tools** - User doesn't know what "tools" are
2. **Don't over-clarify** - Max 2 questions, then execute
3. **Don't ask obvious things** - If they said "recuérdame", they want a task
4. **Don't keep context forever** - After tool call, start fresh

---

## Test Cases

### Test 1: Complete Task
```
Input: "Recuérdame comprar flores para María mañana"
Expected:
  - Reply: Natural confirmation
  - Tool: create_task(title="comprar flores para María", due_at="mañana")
  - Turns: 1
```

### Test 2: Incomplete Task
```
Input: "Recuérdame llamar al dentista"
Expected:
  - Reply: "¿Cuándo quieres que te lo recuerde?"
  - Tool: null

Input: "Pasado mañana"
Expected:
  - Reply: Natural confirmation
  - Tool: create_task(title="llamar al dentista", due_at="pasado mañana")
  - Turns: 2
```

### Test 3: Ambiguous List
```
Input: "Manzanas"
Expected:
  - Reply: "¿A qué lista lo añado?"
  - Tool: null

Input: "Compra"
Expected:
  - Reply: "Listo! Manzanas en tu lista de compra"
  - Tool: add_to_list(list_name="compra", items=["manzanas"])
  - Turns: 2
```

### Test 4: Note (No Questions)
```
Input: "Juan vive en Barcelona"
Expected:
  - Reply: "Anotado! Juan vive en Barcelona"
  - Tool: save_note(content="Juan vive en Barcelona", people=["Juan"])
  - Turns: 1
```

### Test 5: Complex Task
```
Input: "Tengo reunión con el cliente"
Expected:
  - Reply: "¿Cuándo es la reunión?"
  - Tool: null

Input: "Viernes a las 3pm"
Expected:
  - Reply: "Perfecto! Reunión con el cliente el viernes a las 3pm"
  - Tool: create_task(title="reunión con el cliente", due_at="viernes 3pm")
  - Turns: 2
```

---

## Success Criteria

After testing 10 messages:

### ✅ Good Signs:
- Natural questions (¿Cuándo? ¿A qué lista?)
- NOT asking "what do you want to do?"
- Executes after 1-2 questions max
- Uses emojis and friendly language
- Infers task/note/list from context

### ⚠️ Warning Signs:
- Asks "¿Qué quieres hacer?"
- Asks 3+ questions before executing
- Doesn't call tools (always null)
- Always calls tools (never asks questions)
- Generic responses ("Lo siento...")

### ❌ Failure Modes:
- JSON parsing errors (model too small)
- Never infers intent correctly
- Asks inappropriate questions
- Can't maintain context across turns

---

## If It Works:
🎉 **You have a natural conversational bot!**
- Refine responses for even more personality
- Add more contextual intelligence
- Expand to handle edge cases

## If It Fails:
⚠️ **Switch to Option B:**
- LLM generates natural text only
- Orchestrator handles tool logic
- Simpler for small model
- Still feels natural to user

---

**Ready to test! The new prompt should feel much more natural and human-like. 🚀**
