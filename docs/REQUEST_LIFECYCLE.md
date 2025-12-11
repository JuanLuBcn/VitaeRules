# Complete Request Lifecycle - Step by Step

## Example Request: "Hola, puedes detallar en que me puedes ayudar?"

---

## 🚀 PHASE 0: Message Reception (Telegram Layer)

### Step 0.1: User Sends Message
```
User in Telegram app types: "Hola, puedes detallar en que me puedes ayudar?"
    ↓
Telegram servers receive message
    ↓
Telegram Bot API forwards to your bot via webhook/polling
```

### Step 0.2: Bot Handler Receives Message
**File**: `src/app/bot.py` (or similar)

```python
@bot.message_handler()
async def handle_message(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text
    
    logger.info("message_received", extra={
        "user_id": user_id,
        "chat_id": chat_id,
        "text": text
    })
    
    # Start processing
    response = await chat_with_crew_tasks(
        message=text,
        chat_id=str(chat_id),
        user_id=str(user_id)
    )
    
    # Send response back
    await bot.send_message(chat_id, response)
```

**Logged**: `2025-10-31 21:46:32 | INFO | message_received`

---

## 📊 PHASE 1: Intent Analysis (14.70 seconds)

**Objective**: Determine if this is a SEARCH or ACTION intent

### Step 1.1: Initialize ChatCrew
**File**: `src/app/crews/chat/crew.py`
**Time**: 0.04s

```python
def chat_with_crew_tasks(message: str, chat_id: str, user_id: str):
    logger.info("Starting chat_with_crew_tasks")
    
    # Initialize ChatCrew (lazy initialization)
    chat_crew = ChatCrew()
    
    # Initialize agents if not already done
    chat_crew._initialize_agents()  # 0.04s
```

**What happens**:
- Creates CrewAI LLM instance (minimax-m2:cloud)
- Creates Intent Analyzer agent
- Prepares task templates

**Logged**: 
```
Initializing CrewAI agents for ChatCrew
CrewAI LLM created
Agent initialization took 0.04s
```

---

### Step 1.2: Build Intent Detection Task
**File**: `src/app/crews/chat/crew.py` (lines ~185-230)

```python
intent_task = Task(
    description=f"""Analyze this user message and determine the primary intent:

    User message: "{message}"
    
    Recent conversation history:
    {conversation_history}
    
    Classify as ONE of these TWO categories:
    
    **SEARCH**: The user wants to retrieve or query information
    - Questions about stored data (memories, tasks, lists)
    - Questions about past events or conversations
    - General knowledge questions
    - Uses question words: What, When, Where, Who, How, Why, Do, Is, Are
    
    **ACTION**: The user wants to store, create, modify, or communicate (DEFAULT)
    - Statements with new information or events
    - Commands to store, modify, or delete data
    - Social interactions (greetings, thanks, acknowledgments)
    - When in doubt, choose ACTION
    
    Output format:
    Primary Intent: [SEARCH/ACTION]
    Reasoning: [Brief explanation]
    """,
    agent=intent_analyzer_agent,
    expected_output="Intent classification (SEARCH or ACTION) with reasoning"
)
```

**Context included**:
- Current message: "Hola, puedes detallar en que me puedes ayudar?"
- Recent conversation history (from STM - Short Term Memory)

---

### Step 1.3: Execute Intent Detection
**Time**: 14.70s (LLM call)

```python
crew = Crew(
    agents=[intent_analyzer_agent],
    tasks=[intent_task],
    verbose=True,
    process=Process.sequential
)

result = crew.kickoff()
```

**What happens**:
1. CrewAI crew starts execution
2. Intent Analyzer agent processes the task
3. **LLM Call #1** to minimax-m2:cloud
4. LLM analyzes the message
5. Returns classification

**LLM Input**:
```
Message: "Hola, puedes detallar en que me puedes ayudar?"
Context: [previous conversation history]
Task: Classify as SEARCH or ACTION
```

**LLM Output**:
```
Primary Intent: SEARCH
Reasoning: The user is asking a direct question "puedes detallar en que me 
puedes ayudar?" (can you detail what you can help me with?) which uses the 
interrogative "can" and is specifically requesting information about my 
capabilities and services. This is a query about stored information regarding 
my functionality, making it a SEARCH intent rather than an action request.
```

**Logged**:
```
🚀 Crew: crew
└── 📋 Task: 3991d303-0915-47ef-a8c0-c62021131e5f
    Assigned to: Intent Analyzer
    Status: ✅ Completed
    
Intent crew.kickoff() completed in 14.70s
```

---

### Step 1.4: Parse Intent from Output
**File**: `src/app/crews/chat/crew.py` (lines ~265-285)

```python
def _parse_intent(self, output: str) -> ConversationIntent:
    """Parse intent from crew output."""
    output_upper = output.upper()
    
    if "SEARCH" in output_upper:
        return ConversationIntent.SEARCH
    else:
        return ConversationIntent.ACTION  # Default
```

**Result**: Intent = `ConversationIntent.SEARCH`

**Logged**:
```
SEARCH intent detected in output: Primary Intent: SEARCH...
Delegating to UnifiedSearchCrew
```

---

### Step 1.5: Route to Appropriate Crew
**File**: `src/app/crews/chat/crew.py`

```python
if intent == ConversationIntent.SEARCH:
    # Delegate to SearchCrew
    search_result = await unified_search_crew.search(
        query=message,
        context=SearchContext(chat_id=chat_id, user_id=user_id)
    )
    
elif intent == ConversationIntent.ACTION:
    # Delegate to CaptureCrew
    capture_result = await capture_crew.capture(
        message=message,
        chat_id=chat_id,
        user_id=user_id
    )
```

**Decision**: Route to `UnifiedSearchCrew`

---

## 🔍 PHASE 2: Search Execution (~68 seconds)

**Objective**: Search for relevant information across data sources

### Step 2.1: Initialize UnifiedSearchCrew
**File**: `src/app/crews/search/crew.py`
**Time**: ~0.1s

```python
def search(self, query: str, context: SearchContext):
    logger.info("Starting crew.kickoff() for unified search")
    
    # Initialize agents if needed
    self._initialize_agents()
    
    # Create agents:
    # - Search Coordinator
    # - Memory Searcher
    # - Task Searcher
    # - List Searcher
    # - Result Aggregator
```

**Logged**:
```
Initializing CrewAI agents for UnifiedSearchCrew
CrewAI LLM created
CrewAI agents created successfully
```

---

### Step 2.2: Task 1 - Search Coordination
**Agent**: Search Coordinator
**Time**: ~12-15s (LLM call #2)

```python
coordination_task = Task(
    description=f"""Analyze this search query and determine the best search strategy:

    Query: "Hola, puedes detallar en que me puedes ayudar?"
    Available sources: memory, tasks, lists

    Determine:
    1. Which sources are most relevant to this query?
    2. What are the key search terms and entities?
    3. How should results be prioritized?

    Output a search strategy with recommended sources and search criteria.
    """,
    agent=search_coordinator_agent,
    expected_output="Search strategy with recommended sources and criteria"
)

result = coordination_task.execute()
```

**LLM Output** (simplified):
```
**Source Relevance Assessment:**
- Memory: LOW RELEVANCE
- Tasks: LOW RELEVANCE
- Lists: LOW RELEVANCE

**Key Search Terms**: "ayudar" (help), "detallar" (detail)
**Intent**: General capability inquiry, NOT data retrieval

**Recommended Strategy**: Direct response explaining capabilities 
rather than searching personal data sources.
```

**Logged**:
```
🚀 Crew: crew
└── 📋 Task: 0c875e14-e898-4692-bc26-fc6c2ff99115
    Assigned to: Search Coordinator
    Status: ✅ Completed
```

---

### Step 2.3: Task 2 - Memory Search
**Agent**: Memory Searcher
**Time**: ~12s (LLM call #3)
**Status**: ⚠️ Should have been skipped (LOW RELEVANCE)

```python
memory_search_task = Task(
    description=f"""Search long-term memory based on the coordinator's strategy:

    Query: "Hola, puedes detallar en que me puedes ayudar?"

    Use the search criteria from the coordinator to:
    1. Search memory with appropriate filters
    2. Retrieve relevant memories ranked by similarity
    3. Include metadata (timestamps, people, locations, tags)

    Return the top matching memories with their details.
    """,
    agent=memory_searcher_agent,
    context=[coordination_task],  # Has access to coordinator's output
    expected_output="List of relevant memories with metadata"
)

result = memory_search_task.execute()
```

**What the agent does**:
1. Reads coordinator's recommendation (LOW RELEVANCE)
2. Searches anyway (hard-coded workflow)
3. Vector DB search for: "ayudar", "detallar", "capabilities"
4. Finds: **0 results**

**LLM Output**:
```
No memories found in the long-term memory database that match this 
capability inquiry. This appears to be a general question about available 
assistance rather than a request to retrieve specific stored information.
```

**Logged**:
```
🚀 Crew: crew
├── 📋 Task: 94719c76-6659-42fc-92de-90db116acc1a
    Assigned to: Memory Searcher
    Status: ✅ Completed
```

**Time wasted**: ~12s (should have been skipped)

---

### Step 2.4: Task 3 - Task Search
**Agent**: Task Searcher
**Time**: ~12s (LLM call #4)
**Status**: ⚠️ Should have been skipped (LOW RELEVANCE)

```python
task_search_task = Task(
    description=f"""Search tasks and reminders based on the coordinator's strategy:

    Query: "Hola, puedes detallar en que me puedes ayudar?"

    Use the search criteria from the coordinator to:
    1. Search tasks with appropriate filters (status, due date, priority)
    2. Retrieve relevant tasks ranked by relevance
    3. Include metadata (title, due date, priority, status, description)

    Return the top matching tasks with their details.
    """,
    agent=task_searcher_agent,
    context=[coordination_task],
    expected_output="List of relevant tasks with metadata"
)

result = task_search_task.execute()
```

**What the agent does**:
1. Reads coordinator's recommendation (LOW RELEVANCE)
2. Searches anyway (hard-coded workflow)
3. SQL query for tasks matching: "ayudar", "capability"
4. Finds: **0 results**

**LLM Output** (agent explains its capabilities instead):
```
I understand you're asking about my capabilities as a Task Searcher...

**Available Assistance Capabilities Search Results:**
- Status Filtering: Retrieve tasks by completion status
- Priority Classification: Search urgent vs. normal priority
- Due Date Management: Filter by overdue, today, upcoming

Note: Your current query is a general capability inquiry rather than 
a specific task search request.
```

**Logged**:
```
🚀 Crew: crew
├── 📋 Task: f749e58c-cbae-493e-b5a8-3c205bf914b8
    Assigned to: Task Searcher
    Status: ✅ Completed
```

**Time wasted**: ~12s (should have been skipped)

---

### Step 2.5: Task 4 - List Search
**Agent**: List Searcher
**Time**: ~12s (LLM call #5)
**Status**: ⚠️ Should have been skipped (LOW RELEVANCE)

```python
list_search_task = Task(
    description=f"""Search lists and list items based on the coordinator's strategy:

    Query: "Hola, puedes detallar en que me puedes ayudar?"

    Use the search criteria from the coordinator to:
    1. Search list names and item contents
    2. Retrieve relevant items with their list context
    3. Include metadata (list name, position, status, tags, location)

    Return the top matching list items grouped by list.
    """,
    agent=list_searcher_agent,
    context=[coordination_task],
    expected_output="List of relevant list items with metadata"
)

result = list_search_task.execute()
```

**What the agent does**:
1. Reads coordinator's recommendation (LOW RELEVANCE)
2. Searches anyway (hard-coded workflow)
3. SQL query for lists matching: "ayudar", "detallar"
4. Finds: **0 results**

**LLM Output**:
```
After searching through available lists for content related to "ayudar" 
(help), "detallar" (detail), and assistance capabilities, I found no 
matching list items in the current system. This appears to be a general 
capability inquiry rather than a search for specific stored data.
```

**Logged**:
```
🚀 Crew: crew
├── 📋 Task: e2bacfc8-1295-425f-86d8-e527673d141c
    Assigned to: List Searcher
    Status: ✅ Completed
```

**Time wasted**: ~12s (should have been skipped)

---

### Step 2.6: Task 5 - Result Aggregation
**Agent**: Result Aggregator
**Time**: ~15-20s (LLM call #6)

```python
aggregation_task = Task(
    description=f"""Combine search results from all sources into a unified response:

    Original query: "Hola, puedes detallar en que me puedes ayudar?"

    Using results from previous tasks:

    IF RESULTS WERE FOUND (memories, tasks, or lists):
    1. Deduplicate similar results across sources
    2. Rank all results by relevance to the original query
    3. Format into a clear, user-friendly response

    IF NO RESULTS WERE FOUND in any source:
    1. Determine if this is a general knowledge question or personal question
    2. General knowledge questions → Answer using your general knowledge
    3. Personal questions → Ask for clarification

    Make the response concise but informative.
    """,
    agent=result_aggregator_agent,
    context=[coordination_task, memory_search_task, task_search_task, list_search_task],
    expected_output="Unified response combining all search results"
)

result = aggregation_task.execute()
```

**What the agent does**:
1. Receives results from all searchers: **all empty**
2. Determines: This is a **general knowledge question** about capabilities
3. Uses **LLM general knowledge fallback**
4. Generates comprehensive answer in Spanish

**LLM Output**:
```
¡Hola! Como Result Aggregator de MiniMax, soy un experto en síntesis e 
integración de información. Te puedo ayudar de múltiples maneras:

## Mis Capacidades Principales:

### 🔍 **Búsqueda e Integración Multi-fuente**
- Busco y combino resultados de: memorias, tareas, listas
- Elimino duplicados y ranking por relevancia
- Considero: recencia, importancia y similitud semántica

### 📊 **Análisis de Resultados**
- Resumen por tipo de fuente
- Contexto: fechas, personas, etiquetas
- Puntajes de relevancia y recomendaciones

[... detailed capabilities explanation ...]

**¿En qué te gustaría que te ayude hoy?**
```

**Logged**:
```
🚀 Crew: crew
├── 📋 Task: a1138d37-e294-4f03-904c-0b4270b68916
    Assigned to: Result Aggregator
    Status: ✅ Completed

Crew.kickoff() completed successfully for search
```

---

### Step 2.7: Handle Search Completion
**File**: `src/app/crews/chat/crew.py`

```python
try:
    search_result = search_crew.search(query, context)
    
    # Extract combined summary from search result
    response_text = search_result.combined_summary
    
except AttributeError as e:
    # Bug: SearchResult object structure issue
    logger.error(f"Search delegation failed: {e}")
    response_text = "Search error occurred"
```

**Issue**: SearchResult object doesn't have expected `.results` attribute
**Result**: Error logged, but flow continues with fallback

**Logged**:
```
Search delegation failed: 'SearchResult' object has no attribute 'results'
```

---

## 💬 PHASE 3: Response Composition (22.00 seconds)

**Objective**: Create polished final response for user

### Step 3.1: Task 6 - Conversational Assistant
**Agent**: Conversational Assistant
**Time**: ~10-12s (LLM call #7)

```python
chat_task = Task(
    description=f"""Based on the intent analysis, handle the user's message:

    User message: "Hola, puedes detallar en que me puedes ayudar?"
    Intent from previous analysis: SEARCH

    Search results from UnifiedSearchCrew:
    {search_results}  # Actually contains error message due to bug

    If SEARCH:
    - Integrate the search results naturally into your response
    - Cite the information found
    - Be helpful and informative
    - If no results found, the search crew may have provided a general 
      knowledge answer or asked for clarification

    Provide a clear, helpful response appropriate to the intent.
    """,
    agent=conversational_assistant_agent,
    expected_output="Natural response addressing user's message"
)

result = chat_task.execute()
```

**What the agent does**:
1. Sees: SEARCH intent + search error message
2. Knows: User asked about capabilities
3. Generates: Capability explanation from its own knowledge

**LLM Output**:
```
Hola! Me complace saludarte. Soy tu asistente conversacional de MiniMax y 
estoy aquí para ayudarte de múltiples maneras.

Puedo asistirte con una amplia variedad de tareas:

🧠 **Información y Investigación**: Puedo buscar información actualizada 
sobre cualquier tema que necesites...

💬 **Conversación y Asesoramiento**: Estoy diseñado para mantener 
conversaciones naturales, responder preguntas complejas...

📝 **Análisis de Texto**: Puedo revisar, analizar y comentar sobre 
documentos, textos...

🔍 **Búsquedas Especializadas**: Puedo realizar búsquedas web...

🎯 **Resolución de Problemas**: Te ayudo a analizar situaciones...

¿Hay algo específico en lo que te gustaría que te ayude hoy?
```

**Logged**:
```
🚀 Crew: crew
├── 📋 Task: 88bad7f2-749d-409c-82d6-aa2f085ae00f
    Assigned to: Conversational Assistant
    Status: ✅ Completed
```

---

### Step 3.2: Task 7 - Response Composer (Polish)
**Agent**: Response Composer
**Time**: ~10-12s (LLM call #8)

```python
compose_task = Task(
    description=f"""Compose the final response to the user:

    Original message: "Hola, puedes detallar en que me puedes ayudar?"
    Intent: SEARCH
    Response: [From chat agent]

    Create a natural, polished final response that:
    1. Addresses the user's message appropriately
    2. Maintains conversation flow and context
    3. Is friendly, helpful, and clear
    4. Integrates search results naturally (if SEARCH)
    5. Confirms actions (if ACTION)

    Make the response concise but complete, warm but professional.
    """,
    agent=response_composer_agent,
    expected_output="Polished final response ready to send to user"
)

result = compose_task.execute()
```

**What the agent does**:
1. Takes the chat agent's response
2. Polishes language and structure
3. Adds appropriate formatting (emojis, sections)
4. Ensures professional yet friendly tone

**LLM Output** (FINAL):
```
¡Hola! Me da mucho gusto saludarte. Permíteme contarte detalladamente 
cómo puedo ayudarte en MiniMax:

**🔍 Búsquedas e Investigación**: Puedo realizar búsquedas web 
especializadas para encontrar información actualizada sobre cualquier tema 
que necesites - desde noticias actuales, datos de empresas, información 
sobre eventos, hasta datos históricos o técnicos específicos.

**💭 Conversación Inteligente**: Estoy aquí para mantener conversaciones 
naturales, responder tus preguntas más complejas, explicar conceptos que 
no comprendas, o simplemente charlar sobre temas que te interesen.

**📄 Análisis de Contenido**: Puedo revisar y analizar documentos, textos, 
correos, o cualquier material que compartas conmigo - desde análisis de 
tono hasta extracción de información clave.

**🛠️ Resolución Práctica**: Me especializo en ayudarte a desglosar problemas 
complejos y encontrar soluciones paso a paso, ya sea para proyectos 
personales, decisiones importantes, o tareas profesionales.

**⚡ Búsqueda en Tiempo Real**: Si necesitas información que acaba de 
ocurrir o datos muy específicos, puedo acceder a fuentes actualizadas para 
darte la información más reciente.

Mi objetivo es ser tu compañero de confianza - amigable pero profesional, 
conciso pero completo. ¿Hay algún proyecto específico en el que te 
gustaría que trabajemos juntos hoy?
```

**Logged**:
```
🚀 Crew: crew
├── 📋 Task: eb6c8128-078c-4aad-8e2b-0833cfab6f01
    Assigned to: Response Composer
    Status: ✅ Completed

Chat+compose crew.kickoff() completed in 22.00s
```

---

## 💾 PHASE 4: Memory Saving (0.06 seconds)

### Step 4.1: Save to Short-Term Memory
**File**: `src/app/crews/chat/crew.py`
**Time**: 0.06s

```python
# Save interaction to STM
memory_service.save_to_stm(
    chat_id=chat_id,
    user_id=user_id,
    role="user",
    content=message
)

memory_service.save_to_stm(
    chat_id=chat_id,
    user_id=user_id,
    role="assistant",
    content=final_response
)
```

**What happens**:
- User message saved to STM (Short-Term Memory)
- Assistant response saved to STM
- STM persists for this session (until ACTION triggers LTM save)
- Next message will have this in conversation history

**Logged**:
```
Memory saving took 0.06s
```

---

## 📤 PHASE 5: Response Delivery

### Step 5.1: Return Response to Bot Handler
**File**: `src/app/crews/chat/crew.py`

```python
return final_response  # Polished response from composer
```

### Step 5.2: Send to User via Telegram
**File**: `src/app/bot.py`

```python
# Response received from chat_with_crew_tasks()
response = await chat_with_crew_tasks(message, chat_id, user_id)

# Send via Telegram API
await bot.send_message(chat_id, response)
```

**Logged**:
```
⏰ TOTAL chat_with_crew_tasks: 105.25s
message_processed
```

### Step 5.3: User Receives Response
```
Telegram Bot → Telegram Servers → User's Telegram App

User sees:
"¡Hola! Me da mucho gusto saludarte. Permíteme contarte detalladamente 
cómo puedo ayudarte en MiniMax..."
```

---

## 📊 Complete Summary

### Total Time: **105.25 seconds** (1 minute 45 seconds)

### Phase Breakdown:
| Phase | Time | % of Total |
|-------|------|------------|
| Phase 1: Intent Analysis | 14.70s | 14% |
| Phase 2: Search Execution | ~68s | 65% |
| Phase 3: Response Composition | 22.00s | 21% |
| Phase 4: Memory Saving | 0.06s | <1% |
| Phase 5: Response Delivery | <0.5s | <1% |

### LLM Calls: **8 total**
| # | Agent | Phase | Time | Purpose |
|---|-------|-------|------|---------|
| 1 | Intent Analyzer | 1 | 14.70s | SEARCH/ACTION classification |
| 2 | Search Coordinator | 2 | ~12s | Determine search strategy |
| 3 | Memory Searcher | 2 | ~12s | Search memories (wasted) |
| 4 | Task Searcher | 2 | ~12s | Search tasks (wasted) |
| 5 | List Searcher | 2 | ~12s | Search lists (wasted) |
| 6 | Result Aggregator | 2 | ~15s | General knowledge fallback |
| 7 | Conversational Assistant | 3 | ~11s | Generate response |
| 8 | Response Composer | 3 | ~11s | Polish response |

### Data Flow:
```
User Message
    ↓
Intent Detection → SEARCH
    ↓
Search Coordination → "LOW RELEVANCE for all"
    ↓
Memory Search → 0 results (should have skipped)
    ↓
Task Search → 0 results (should have skipped)
    ↓
List Search → 0 results (should have skipped)
    ↓
Result Aggregation → General knowledge answer
    ↓
Chat Response → Capability explanation
    ↓
Polish Response → Final formatted answer
    ↓
Save to Memory → STM updated
    ↓
Telegram → User receives message
```

### Optimization Opportunities:
1. **Skip unnecessary searches**: ~36-48s savings
2. **Merge response composition**: ~11s savings
3. **Parallel search execution**: ~24s savings (if searches run in parallel)

**Potential optimized time**: **~45-50 seconds** (50% faster!)

---

## 🔄 Alternative Flow: ACTION Intent

For comparison, if the message was: "Hoy fuimos a la oficina con Biel"

```
Intent Detection (14s) → ACTION
    ↓
CaptureCrew:
  ├─ Action Planner (12s) → Tools: [memory.note]
  ├─ Tool Executor (12s) → Execute: save memory
  └─ Response Composer (11s) → "He guardado que..."
    ↓
Memory Save (0.06s) → LTM + STM
    ↓
Response to User (0.5s)

Total: ~50 seconds (4 LLM calls instead of 8)
```

---

## 🎯 Key Takeaways

1. **Intent detection is fast** (14.7s) and accurate with minimax-m2:cloud
2. **Search phase is the bottleneck** (68s) due to unnecessary searches
3. **Response composition is reasonable** (22s) for quality output
4. **Total of 8 LLM calls** for a simple capability inquiry
5. **Optimization potential**: Almost 50% time reduction possible

Would you like me to implement any of these optimizations?
