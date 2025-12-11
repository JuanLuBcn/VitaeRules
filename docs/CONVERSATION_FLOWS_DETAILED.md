# Agent Zero: Conversation Flow & Prompt Design

## Overview

Agent Zero uses a **two-phase approach**:
1. **Intent Detection** - Classify what user wants (fast, small LLM)
2. **Agent Routing** - Delegate to specialist, synthesize response

---

## Phase 1: Intent Detection

### How It Works

```
User Message
    ↓
IntentDetector analyzes with lean prompt
    ↓
Returns: {
  "intent": "MEMORY_STORE" | "MEMORY_QUERY" | "TASK_CREATE" | "LIST_ADD" | "CHAT" | "COMPOSITE",
  "entities": {...extracted data...},
  "confidence": 0.95
}
```

### Intent Detector Prompt

```python
INTENT_DETECTION_PROMPT = """Analiza el mensaje del usuario y clasifica su intención.

Usuario: "{message}"

INTENTS posibles:
1. MEMORY_STORE - Quiere guardar información para recordar
   Ejemplos: "Guarda que...", "María me dijo que...", "Apunta que..."
   
2. MEMORY_QUERY - Quiere buscar información guardada
   Ejemplos: "¿Qué me dijo...?", "¿Cuándo fue...?", "Busca..."
   
3. TASK_CREATE - Quiere crear un recordatorio o tarea
   Ejemplos: "Recuérdame...", "Tengo que...", "No olvides..."
   
4. LIST_ADD - Quiere añadir a una lista
   Ejemplos: "Añade leche", "Comprar pan", "Agregar a la lista..."
   
5. CHAT - Conversación general, pregunta, opinión
   Ejemplos: "¿Qué opinas de...?", "Hola", "¿Cómo estás?"
   
6. COMPOSITE - Múltiples intenciones en un mensaje
   Ejemplo: "Recuérdame llamar a Juan y guarda que le gusta el fútbol"

Extrae también:
- Entidades (personas, fechas, lugares)
- Datos relevantes

JSON:
{{
  "intent": "...",
  "confidence": 0.0-1.0,
  "entities": {{
    // Datos extraídos según el intent
  }}
}}

REGLAS:
- Si no estás seguro → CHAT
- Si hay múltiples acciones → COMPOSITE
- Extrae toda la información posible
"""
```

### Entity Extraction by Intent

**MEMORY_STORE entities:**
```json
{
  "content": "text to store",
  "people": ["Juan", "María"],
  "tags": ["work", "personal"],
  "context": "additional context"
}
```

**MEMORY_QUERY entities:**
```json
{
  "query": "what user wants to find",
  "people": ["Juan"],
  "time_range": "last week",
  "topic": "Barcelona"
}
```

**TASK_CREATE entities:**
```json
{
  "title": "llamar a Juan",
  "due_at": "mañana 3pm",
  "description": "hablar sobre el proyecto",
  "people": ["Juan"]
}
```

**LIST_ADD entities:**
```json
{
  "items": ["leche", "pan", "huevos"],
  "list_name": "compra"  // can be null (to ask)
}
```

**COMPOSITE entities:**
```json
{
  "actions": [
    {"intent": "TASK_CREATE", "data": {...}},
    {"intent": "MEMORY_STORE", "data": {...}}
  ]
}
```

---

## Phase 2: Agent Routing & Response

### Agent Zero Flow

```
Intent Detection Result
    ↓
Agent Zero routes to specialist agent
    ↓
Agent executes (may ask questions)
    ↓
Agent returns result
    ↓
Agent Zero synthesizes natural response
    ↓
Send to user
```

---

## Detailed Flow Examples

### Example 1: Simple Memory Store

**User:** "María me dijo que se muda a Barcelona en marzo"

```
┌─────────────────────────────────────────────┐
│ STEP 1: Intent Detection                   │
└─────────────────────────────────────────────┘

IntentDetector analyzes:
  Message: "María me dijo que se muda a Barcelona en marzo"
  
  → Intent: MEMORY_STORE
  → Confidence: 0.95
  → Entities:
    {
      "content": "María se muda a Barcelona en marzo",
      "people": ["María"],
      "tags": ["mudanza", "Barcelona"],
      "context": "conversation"
    }

┌─────────────────────────────────────────────┐
│ STEP 2: Route to MemoryAgent                │
└─────────────────────────────────────────────┘

Agent Zero calls:
  await memory_agent.store(
    user_id="user123",
    content="María se muda a Barcelona en marzo",
    people=["María"],
    tags=["mudanza", "Barcelona"]
  )

MemoryAgent:
  1. Creates MemoryItem
  2. Stores in vector DB
  3. Returns: {"success": True, "memory_id": "mem_abc123"}

┌─────────────────────────────────────────────┐
│ STEP 3: Synthesize Response                 │
└─────────────────────────────────────────────┘

Agent Zero generates natural response:
  Prompt: """
  Action performed: Stored memory about María moving to Barcelona
  
  Generate a natural confirmation in Spanish.
  Keep it short and friendly.
  """
  
  → Response: "Anotado! María se muda a Barcelona en marzo 📝"

┌─────────────────────────────────────────────┐
│ STEP 4: Send to User                        │
└─────────────────────────────────────────────┘

Bot → User: "Anotado! María se muda a Barcelona en marzo 📝"

[DONE - Single turn]
```

---

### Example 2: Memory Query (with context)

**User:** "¿Qué me contó María la semana pasada?"

```
┌─────────────────────────────────────────────┐
│ STEP 1: Intent Detection                   │
└─────────────────────────────────────────────┘

IntentDetector analyzes:
  Message: "¿Qué me contó María la semana pasada?"
  
  → Intent: MEMORY_QUERY
  → Confidence: 0.98
  → Entities:
    {
      "query": "qué me contó María",
      "people": ["María"],
      "time_range": "last week"
    }

┌─────────────────────────────────────────────┐
│ STEP 2: Route to SearchAgent                │
└─────────────────────────────────────────────┘

Agent Zero calls:
  await search_agent.search(
    user_id="user123",
    query="María",
    filters={
      "people": ["María"],
      "date_range": {
        "start": "2025-10-21",
        "end": "2025-10-27"
      }
    },
    limit=5
  )

SearchAgent (RetrievalCrew):
  1. Vector search: "María"
  2. Filter by date: last week
  3. Filter by people: María
  4. Rank by relevance
  
  Returns:
    [
      {
        "content": "María se muda a Barcelona en marzo",
        "date": "2025-10-25",
        "score": 0.92
      },
      {
        "content": "María le gustan las flores",
        "date": "2025-10-23",
        "score": 0.85
      }
    ]

┌─────────────────────────────────────────────┐
│ STEP 3: Synthesize Response                 │
└─────────────────────────────────────────────┘

Agent Zero generates response WITH context:

  Prompt: """
  User asked: "¿Qué me contó María la semana pasada?"
  
  Found memories:
  1. "María se muda a Barcelona en marzo" (Oct 25)
  2. "María le gustan las flores" (Oct 23)
  
  Synthesize a natural response in Spanish that:
  - Answers the question
  - Presents the information chronologically
  - Is conversational (not a list)
  """
  
  LLM generates:
    "La semana pasada hablaste con María sobre dos cosas:
    
    El 23 de octubre mencionaste que le gustan las flores.
    
    Y el 25 te contó que se muda a Barcelona en marzo 🏙️"

┌─────────────────────────────────────────────┐
│ STEP 4: Send to User                        │
└─────────────────────────────────────────────┘

Bot → User: [Generated response above]

[DONE - Single turn with synthesized context]
```

---

### Example 3: Task Creation (needs enrichment)

**User:** "Recuérdame llamar a Juan"

```
┌─────────────────────────────────────────────┐
│ STEP 1: Intent Detection                   │
└─────────────────────────────────────────────┘

IntentDetector analyzes:
  Message: "Recuérdame llamar a Juan"
  
  → Intent: TASK_CREATE
  → Confidence: 0.99
  → Entities:
    {
      "title": "llamar a Juan",
      "due_at": null,  ← MISSING!
      "people": ["Juan"]
    }

┌─────────────────────────────────────────────┐
│ STEP 2: Route to TaskAgent                  │
└─────────────────────────────────────────────┘

Agent Zero calls:
  await task_agent.create_task(
    user_id="user123",
    title="llamar a Juan",
    due_at=None,  ← Missing!
    people=["Juan"]
  )

TaskAgent detects missing field:
  - Required: due_at
  - Action: Ask user
  
  Returns:
    {
      "status": "needs_info",
      "missing_field": "due_at",
      "question": "¿Cuándo quieres que te lo recuerde?",
      "partial_data": {
        "title": "llamar a Juan",
        "people": ["Juan"]
      }
    }

┌─────────────────────────────────────────────┐
│ STEP 3: Agent Zero asks user                │
└─────────────────────────────────────────────┘

Agent Zero receives "needs_info" response:
  1. Saves context:
     {
       "agent": "task_agent",
       "action": "create_task",
       "waiting_for": "due_at",
       "partial_data": {...}
     }
  
  2. Sends question to user

Bot → User: "¿Cuándo quieres que te lo recuerde?"

[WAITING for user response]

┌─────────────────────────────────────────────┐
│ TURN 2: User answers                         │
└─────────────────────────────────────────────┘

User: "Mañana a las 3pm"

Agent Zero detects context exists:
  - Agent: task_agent
  - Waiting for: due_at
  - Action: create_task

Agent Zero parses answer:
  Prompt: """
  User was asked: "¿Cuándo quieres que te lo recuerde?"
  User answered: "Mañana a las 3pm"
  
  Extract the due_at value.
  Today is: 2025-10-28
  
  JSON: {{"due_at": "YYYY-MM-DD HH:MM"}}
  """
  
  → Result: {"due_at": "2025-10-29 15:00"}

Agent Zero calls TaskAgent again:
  await task_agent.create_task(
    user_id="user123",
    title="llamar a Juan",
    due_at="2025-10-29 15:00",
    people=["Juan"]
  )

TaskAgent:
  1. Validates: All fields present ✓
  2. Creates task in DB
  3. Stores in memory (for context)
  
  Returns:
    {
      "status": "success",
      "task_id": "task_xyz789",
      "task": {
        "title": "llamar a Juan",
        "due_at": "2025-10-29 15:00"
      }
    }

┌─────────────────────────────────────────────┐
│ STEP 4: Synthesize Response                 │
└─────────────────────────────────────────────┘

Agent Zero generates confirmation:
  → "Perfecto! Te recordaré mañana a las 3pm llamar a Juan ✅"

Agent Zero clears context

Bot → User: "Perfecto! Te recordaré mañana a las 3pm llamar a Juan ✅"

[DONE - Two turns with enrichment]
```

---

### Example 4: Composite Intent

**User:** "Recuérdame llamar a Juan mañana y guarda que le gusta el fútbol"

```
┌─────────────────────────────────────────────┐
│ STEP 1: Intent Detection                   │
└─────────────────────────────────────────────┘

IntentDetector analyzes:
  Message: "Recuérdame llamar a Juan mañana y guarda que le gusta el fútbol"
  
  → Intent: COMPOSITE
  → Confidence: 0.94
  → Entities:
    {
      "actions": [
        {
          "intent": "TASK_CREATE",
          "data": {
            "title": "llamar a Juan",
            "due_at": "mañana",
            "people": ["Juan"]
          }
        },
        {
          "intent": "MEMORY_STORE",
          "data": {
            "content": "A Juan le gusta el fútbol",
            "people": ["Juan"],
            "tags": ["fútbol"]
          }
        }
      ]
    }

┌─────────────────────────────────────────────┐
│ STEP 2: Route to Multiple Agents            │
└─────────────────────────────────────────────┘

Agent Zero executes actions sequentially:

Action 1: TASK_CREATE
  await task_agent.create_task(
    title="llamar a Juan",
    due_at="mañana",
    people=["Juan"]
  )
  
  → Result: {"status": "success", "task_id": "..."}

Action 2: MEMORY_STORE
  await memory_agent.store(
    content="A Juan le gusta el fútbol",
    people=["Juan"],
    tags=["fútbol"]
  )
  
  → Result: {"success": True, "memory_id": "..."}

┌─────────────────────────────────────────────┐
│ STEP 3: Synthesize Combined Response        │
└─────────────────────────────────────────────┘

Agent Zero generates response for both actions:

  Prompt: """
  User requested two things:
  1. Create task: "llamar a Juan" tomorrow
  2. Store memory: "Juan le gusta el fútbol"
  
  Both completed successfully.
  
  Generate a natural confirmation that acknowledges both actions.
  Spanish, concise, friendly.
  """
  
  → Response: "Te recordaré mañana llamar a Juan. Y anotado que le gusta el fútbol ✅⚽"

Bot → User: "Te recordaré mañana llamar a Juan. Y anotado que le gusta el fútbol ✅⚽"

[DONE - Single turn with multiple actions]
```

---

### Example 5: Chat with Memory Context

**User:** "¿Qué opinas de Barcelona?"

```
┌─────────────────────────────────────────────┐
│ STEP 1: Intent Detection                   │
└─────────────────────────────────────────────┘

IntentDetector analyzes:
  Message: "¿Qué opinas de Barcelona?"
  
  → Intent: CHAT
  → Confidence: 0.88
  → Entities: {"topic": "Barcelona"}

┌─────────────────────────────────────────────┐
│ STEP 2: Route to ChatAgent                  │
└─────────────────────────────────────────────┘

Agent Zero calls ChatAgent, but FIRST gets context:

Step 2.1: Get relevant memories
  await search_agent.search(
    query="Barcelona",
    user_id="user123",
    limit=3
  )
  
  Returns:
    [
      {"content": "María se muda a Barcelona en marzo", "score": 0.92}
    ]

Step 2.2: Call ChatAgent with context
  await chat_agent.respond(
    message="¿Qué opinas de Barcelona?",
    context=[
      "User's friend María is moving to Barcelona in March"
    ]
  )

ChatAgent Prompt:
  """
  You are the user's personal assistant. You know about their life.
  
  User asks: "¿Qué opinas de Barcelona?"
  
  Context from their life:
  - Their friend María is moving to Barcelona in March
  
  Respond naturally in Spanish. Reference the context if relevant.
  Be helpful and conversational.
  """

ChatAgent generates:
  "Barcelona es una ciudad increíble! Tiene una mezcla perfecta de cultura, 
  playa y arquitectura. Por cierto, vi que María se muda allí en marzo - 
  será un gran cambio para ella. ¿Estás pensando en visitarla cuando se instale?"

┌─────────────────────────────────────────────┐
│ STEP 3: Send Response                       │
└─────────────────────────────────────────────┘

Bot → User: [ChatAgent response]

[DONE - Chat with personal context]
```

---

### Example 6: Ambiguous Input (needs clarification)

**User:** "Leche"

```
┌─────────────────────────────────────────────┐
│ STEP 1: Intent Detection                   │
└─────────────────────────────────────────────┘

IntentDetector analyzes:
  Message: "Leche"
  
  → Intent: LIST_ADD (most likely)
  → Confidence: 0.65 (not very confident)
  → Entities:
    {
      "items": ["leche"],
      "list_name": null  ← Unknown!
    }

┌─────────────────────────────────────────────┐
│ STEP 2: Route to ListAgent                  │
└─────────────────────────────────────────────┘

Agent Zero calls:
  await list_agent.add_items(
    user_id="user123",
    items=["leche"],
    list_name=None  ← Missing!
  )

ListAgent options:
  Option A: Ask which list
  Option B: Infer from user's lists
  
  ListAgent checks user's existing lists:
    - "Compras" (90% of items)
    - "Tareas" (empty)
  
  ListAgent decides: ASK (safer)
  
  Returns:
    {
      "status": "needs_info",
      "missing_field": "list_name",
      "question": "¿A qué lista añado leche?",
      "suggestions": ["Compras", "Tareas"],
      "partial_data": {"items": ["leche"]}
    }

┌─────────────────────────────────────────────┐
│ STEP 3: Agent Zero asks with suggestions    │
└─────────────────────────────────────────────┘

Agent Zero receives "needs_info":
  1. Saves context
  2. Generates question with suggestions

Bot → User: "¿A qué lista añado leche? (Compras, Tareas)"

[WAITING]

┌─────────────────────────────────────────────┐
│ TURN 2: User answers                         │
└─────────────────────────────────────────────┘

User: "Compras"

Agent Zero:
  1. Retrieves context
  2. Extracts list_name: "Compras"
  3. Calls ListAgent again

ListAgent:
  1. Adds "leche" to "Compras" list
  2. Returns success

Bot → User: "Listo! Leche en tu lista de Compras 🛒"

[DONE - Two turns with clarification]
```

---

## Agent Zero Implementation

### Core Structure

```python
class AgentZero:
    """
    Your personal AI assistant.
    Single personality that knows your entire life.
    """
    
    def __init__(self, llm_service, memory_service):
        self.llm = llm_service
        self.memory = memory_service
        
        # Specialized workers
        self.intent_detector = IntentDetector(llm_service)
        self.memory_agent = MemoryAgent(memory_service)
        self.task_agent = TaskAgent(llm_service)
        self.list_agent = ListAgent()
        self.search_agent = SearchAgent(memory_service)
        self.chat_agent = ChatAgent(llm_service)
        
        # Conversation context (for multi-turn)
        self.contexts = {}  # {chat_id: {...}}
    
    async def handle_message(self, message: str, chat_id: str, user_id: str):
        """
        Main entry point.
        Handles all user messages.
        """
        
        # Check if we're in a multi-turn conversation
        context = self.contexts.get(chat_id)
        
        if context and context.get("waiting_for"):
            # We asked a question, this is the answer
            return await self._handle_answer(message, context, chat_id, user_id)
        
        else:
            # New request
            return await self._handle_new_request(message, chat_id, user_id)
    
    async def _handle_new_request(self, message, chat_id, user_id):
        """Handle new user request."""
        
        # Step 1: Detect intent
        intent_result = await self.intent_detector.detect(message)
        
        intent = intent_result["intent"]
        entities = intent_result["entities"]
        confidence = intent_result.get("confidence", 0.0)
        
        self.tracer.info(
            "intent_detected",
            extra={
                "intent": intent,
                "confidence": confidence,
                "entities": list(entities.keys())
            }
        )
        
        # Step 2: Route to appropriate agent
        if intent == "MEMORY_STORE":
            result = await self._handle_memory_store(entities, user_id)
        
        elif intent == "MEMORY_QUERY":
            result = await self._handle_memory_query(entities, user_id)
        
        elif intent == "TASK_CREATE":
            result = await self._handle_task_create(entities, user_id, chat_id)
        
        elif intent == "LIST_ADD":
            result = await self._handle_list_add(entities, user_id, chat_id)
        
        elif intent == "CHAT":
            result = await self._handle_chat(message, user_id)
        
        elif intent == "COMPOSITE":
            result = await self._handle_composite(entities, user_id, chat_id)
        
        else:
            # Fallback
            result = await self._handle_chat(message, user_id)
        
        # Step 3: Check if agent needs more info
        if result.get("status") == "needs_info":
            # Save context for next turn
            self.contexts[chat_id] = {
                "intent": intent,
                "agent": result.get("agent"),
                "action": result.get("action"),
                "waiting_for": result["missing_field"],
                "partial_data": result["partial_data"],
                "original_message": message
            }
            
            # Ask user
            question = result["question"]
            if result.get("suggestions"):
                question += f" ({', '.join(result['suggestions'])})"
            
            return {"message": question, "waiting_for_input": True}
        
        # Step 4: Generate response
        response = await self._synthesize_response(intent, result, message)
        
        return {"message": response, "waiting_for_input": False}
    
    async def _handle_answer(self, answer, context, chat_id, user_id):
        """Handle user's answer to our question."""
        
        agent = context["agent"]
        action = context["action"]
        waiting_for = context["waiting_for"]
        partial_data = context["partial_data"]
        
        # Parse the answer
        parsed_value = await self._parse_answer(
            answer=answer,
            field=waiting_for,
            context=context
        )
        
        # Merge with partial data
        partial_data[waiting_for] = parsed_value
        
        # Retry the agent action
        if agent == "task_agent":
            result = await self.task_agent.create_task(
                user_id=user_id,
                **partial_data
            )
        
        elif agent == "list_agent":
            result = await self.list_agent.add_items(
                user_id=user_id,
                **partial_data
            )
        
        # Check if still needs more info
        if result.get("status") == "needs_info":
            # Update context
            context["waiting_for"] = result["missing_field"]
            context["partial_data"] = result["partial_data"]
            
            return {
                "message": result["question"],
                "waiting_for_input": True
            }
        
        # Success! Clear context
        self.contexts.pop(chat_id, None)
        
        # Generate response
        response = await self._synthesize_response(
            context["intent"],
            result,
            context["original_message"]
        )
        
        return {"message": response, "waiting_for_input": False}
    
    async def _handle_memory_store(self, entities, user_id):
        """Store new memory."""
        
        result = await self.memory_agent.store(
            user_id=user_id,
            content=entities["content"],
            people=entities.get("people", []),
            tags=entities.get("tags", []),
            media=entities.get("media")
        )
        
        return {
            "status": "success",
            "action": "memory_store",
            "content": entities["content"]
        }
    
    async def _handle_memory_query(self, entities, user_id):
        """Query memory."""
        
        results = await self.search_agent.search(
            user_id=user_id,
            query=entities["query"],
            filters={
                "people": entities.get("people"),
                "date_range": entities.get("time_range"),
                "topic": entities.get("topic")
            },
            limit=5
        )
        
        return {
            "status": "success",
            "action": "memory_query",
            "query": entities["query"],
            "results": results
        }
    
    async def _handle_task_create(self, entities, user_id, chat_id):
        """Create task (may need enrichment)."""
        
        result = await self.task_agent.create_task(
            user_id=user_id,
            title=entities.get("title"),
            due_at=entities.get("due_at"),
            description=entities.get("description"),
            people=entities.get("people", [])
        )
        
        # TaskAgent may return "needs_info"
        if result.get("status") == "needs_info":
            result["agent"] = "task_agent"
            result["action"] = "create_task"
        
        return result
    
    async def _handle_chat(self, message, user_id):
        """Handle general conversation with context."""
        
        # Get relevant memories for context
        context = await self.search_agent.search(
            user_id=user_id,
            query=message,
            limit=3
        )
        
        # Generate response
        response = await self.chat_agent.respond(
            message=message,
            context=[r["content"] for r in context]
        )
        
        return {
            "status": "success",
            "action": "chat",
            "response": response
        }
    
    async def _synthesize_response(self, intent, result, original_message):
        """
        Generate natural language response.
        This is where Agent Zero's personality shines!
        """
        
        if intent == "MEMORY_STORE":
            return f"Anotado! {result['content']} 📝"
        
        elif intent == "MEMORY_QUERY":
            if not result["results"]:
                return "No encontré nada sobre eso 🤔"
            
            # Let LLM format results
            prompt = f"""User asked: "{result['query']}"

Found memories:
{self._format_results(result['results'])}

Generate a natural response in Spanish that presents this information conversationally.
Be concise but informative."""
            
            return self.llm.generate(prompt)
        
        elif intent == "TASK_CREATE":
            task = result["task"]
            return f"Te recordaré {task['due_at']} {task['title']} ✅"
        
        elif intent == "LIST_ADD":
            items = result["items"]
            list_name = result["list_name"]
            items_text = ", ".join(items)
            return f"Listo! {items_text} en tu lista de {list_name} 🛒"
        
        elif intent == "CHAT":
            return result["response"]
        
        elif intent == "COMPOSITE":
            # Multiple actions
            return result.get("combined_response", "Hecho! ✅")
        
        return "Hecho! ✅"
```

---

## Prompt Templates

### 1. Intent Detection

```python
INTENT_DETECTION_SYSTEM = """Eres un clasificador de intenciones.
Analiza mensajes y extrae:
1. Intención principal
2. Entidades relevantes
3. Confianza

Responde SOLO con JSON válido."""

INTENT_DETECTION_PROMPT = """Mensaje: "{message}"

Clasifica en: MEMORY_STORE, MEMORY_QUERY, TASK_CREATE, LIST_ADD, CHAT, COMPOSITE

Extrae entidades según la intención.

JSON:
{{
  "intent": "...",
  "confidence": 0.0-1.0,
  "entities": {{...}}
}}"""
```

### 2. Memory Query Response Synthesis

```python
MEMORY_QUERY_SYNTHESIS = """User asked: "{query}"

Found memories:
{results}

Generate a natural conversational response in Spanish that:
- Answers the question directly
- Presents information chronologically if relevant
- Mentions dates if important
- Is concise (2-3 sentences max)
- Uses friendly tone

Response:"""
```

### 3. Chat with Context

```python
CHAT_WITH_CONTEXT = """You are {user_name}'s personal AI assistant.
You know about their life through stored memories.

User asks: "{message}"

Context from their life:
{context}

Respond naturally in Spanish:
- Reference the context if relevant
- Be helpful and conversational
- Don't mention "I found in your memories" - speak as if you just know
- Keep it concise

Response:"""
```

### 4. Parse User Answer

```python
PARSE_ANSWER = """User was asked: "{question}"
User answered: "{answer}"

Extract the value for field: {field}

Context:
- Today is: {today}
- Field type: {field_type}

Parse the answer and return just the value.

JSON:
{{
  "{field}": "parsed_value"
}}"""
```

### 5. Composite Response Synthesis

```python
COMPOSITE_SYNTHESIS = """User said: "{message}"

Multiple actions completed:
{actions}

Generate a single natural confirmation in Spanish that acknowledges all actions.
Be concise, friendly, use emojis.

Response:"""
```

---

## Key Design Principles

### 1. **Two-Phase Processing**
- Phase 1: Intent Detection (fast, lean)
- Phase 2: Agent Execution (specialized)

### 2. **Agent Autonomy**
- Each agent can ask for missing info
- Returns `needs_info` status
- Agent Zero handles the conversation flow

### 3. **Context-Aware Chat**
- Always search memory before chat
- Provide relevant context to ChatAgent
- Feel like talking to someone who knows your life

### 4. **Natural Response Generation**
- LLM generates final response (not templates)
- Personalized, contextual
- Consistent tone

### 5. **Graceful Degradation**
- If intent unclear → CHAT
- If agent fails → Friendly error
- Always respond (never crash)

---

## Implementation Priority

### Phase 1: Core Flow (Week 1)
1. ✅ Intent Detection working
2. ✅ Memory Store/Query working
3. ✅ Basic response synthesis

### Phase 2: Task & List (Week 2)
1. TaskAgent with enrichment
2. ListAgent with clarification
3. Multi-turn conversation handling

### Phase 3: Chat Mode (Week 3)
1. ChatAgent implementation
2. Context injection
3. Personality tuning

### Phase 4: Composite & Polish (Week 4)
1. Composite intent handling
2. Response quality improvements
3. Error handling
4. Testing & refinement

---

## Questions for Discussion

1. **Intent Confidence Threshold**: If confidence < 0.7, should we ask user to clarify or default to CHAT?

2. **Memory in Chat**: Should ChatAgent ALWAYS get memory context, or only when relevant?

3. **Composite Limits**: Max how many actions in one message? (I suggest 3 max)

4. **Enrichment Strategy**: Should agents ask ONE question at a time, or batch multiple questions?

5. **Response Length**: Should we limit synthesis responses to 2-3 sentences or allow longer?

What do you think about these flows and prompts? Should we adjust anything?
