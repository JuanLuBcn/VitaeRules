# VitaeRules: Second Brain Architecture v2

## Vision

**VitaeRules is your personal AI assistant that remembers everything about your life.**

It's ChatGPT, but it knows:
- 🧠 Your memories (conversations, notes, ideas)
- ✅ Your tasks and reminders
- 📝 Your lists (shopping, todos, projects)
- 👥 Your people (friends, family, colleagues)
- 📅 Your events (future feature)
- 📄 Your documents (future feature)
- 🎯 Your goals (future feature)

You talk to it naturally, and it:
1. **Remembers** - Stores important information automatically
2. **Recalls** - Finds anything from your past
3. **Reminds** - Creates tasks and sends reminders
4. **Assists** - Helps with general questions (like ChatGPT)

---

## Core Philosophy

### Memory-First Design

**Everything is memory:**
- A note → Memory
- A task → Memory (with due_date field)
- A list item → Memory (with list field)
- A conversation → Memory
- A photo → Memory (with media)

**Agent Zero always has context of your entire life through vector search.**

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    User (Telegram)                      │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│              Agent Zero (Orchestrator)                  │
│                                                         │
│  Role: Your personal AI assistant                      │
│                                                         │
│  Responsibilities:                                     │
│  • Single personality (you talk to ONE bot)            │
│  • Understands user intent                             │
│  • Routes to specialized agents/crews                  │
│  • Synthesizes final response                          │
│  • Maintains conversational context                    │
│                                                         │
│  Capabilities:                                         │
│  • Normal chat (like ChatGPT)                          │
│  • Query your memory                                   │
│  • Store new memories                                  │
│  • Create tasks/reminders                              │
│  • Manage lists                                        │
│  • (Future: more capabilities)                         │
└────────────┬────────────────────────────────────────────┘
             │
             │ Routes based on intent
             │
    ┌────────┼─────────┬─────────────┬──────────────┬──────────┐
    ▼        ▼         ▼             ▼              ▼          ▼
┌─────────┐┌─────────┐┌──────────┐┌──────────┐┌──────────┐┌─────────┐
│Memory   ││Task     ││List      ││Search    ││Intent    ││Chat     │
│Agent    ││Agent    ││Agent     ││Agent     ││Detector  ││Agent    │
│         ││         ││          ││          ││          ││         │
│Store    ││Create   ││Manage    ││Find info ││Classify  ││General  │
│memories ││tasks    ││lists     ││in memory ││intent    ││convo    │
└─────────┘└─────────┘└──────────┘└──────────┘└──────────┘└─────────┘
     │          │          │             │
     └──────────┴──────────┴─────────────┘
                    │
                    ▼
        ┌────────────────────────┐
        │   Memory Storage       │
        │   (Vector DB + SQLite) │
        │                        │
        │  • Memories            │
        │  • Tasks               │
        │  • Lists               │
        │  • People              │
        │  • All data            │
        └────────────────────────┘
```

---

## Component Breakdown

### 1. Agent Zero (Orchestrator) 🎯

**Role:** The bot's personality. You only talk to Agent Zero.

**Responsibilities:**
- **Conversation:** Maintains natural chat flow
- **Intent Detection:** Understands what you want (uses IntentDetector)
- **Routing:** Delegates to specialized agents
- **Response Synthesis:** Combines results into natural response
- **Context:** Keeps conversation context (last few turns)

**Example Flow:**
```python
User: "Recuérdame llamar a Juan mañana, ah y guarda que le gustan las flores"

Agent Zero thinks:
  1. Detect intent → COMPOSITE (TASK + MEMORY)
  2. Route to TaskAgent → Create task
  3. Route to MemoryAgent → Store note
  4. Synthesize → "Te recordaré mañana llamar a Juan. Y anotado que le gustan las flores ✅"
```

**Capabilities:**
- ✅ Normal conversation (ChatGPT-like)
- ✅ Query memory ("What did I...?")
- ✅ Store memory ("Guarda que...")
- ✅ Create tasks ("Recuérdame...")
- ✅ Manage lists ("Añade a la lista...")
- ✅ Multi-intent handling (multiple actions in one message)

---

### 2. Intent Detector 🔍

**Role:** Classify user messages into intents

**Intents:**
- `MEMORY_STORE` - User wants to save information
- `MEMORY_QUERY` - User wants to retrieve information
- `TASK_CREATE` - User wants a reminder/task
- `LIST_ADD` - User wants to add to a list
- `CHAT` - User wants general conversation
- `COMPOSITE` - Multiple intents in one message

**Why separate?**
- Can be swapped/improved independently
- Can use different models (fast classifier vs main LLM)
- Can log intent accuracy for improvement

---

### 3. Memory Agent 💾

**Role:** Store and retrieve unstructured memories

**Operations:**
- `store(content, people, tags, media)` → Store new memory
- `update(memory_id, ...)` → Update existing memory
- `delete(memory_id)` → Delete memory

**What it stores:**
- Notes ("María likes flowers")
- Conversation snippets
- Ideas
- Facts about people
- Media with descriptions

**NOT responsible for:**
- Tasks (that's TaskAgent)
- Lists (that's ListAgent)
- Searching (that's SearchAgent)

---

### 4. Task Agent ✅

**Role:** Manage tasks and reminders

**Operations:**
- `create_task(title, due_at, ...)` → Create task
- `list_tasks(status, due_date_range)` → Query tasks
- `complete_task(task_id)` → Mark done
- `update_task(task_id, ...)` → Update task

**Enrichment:**
- Can ask for missing fields (when?, who?)
- Validates dates (not in past)
- Parses natural language dates

**Integration with Memory:**
- Tasks are ALSO stored in memory (for context)
- User can ask "What tasks do I have?" → SearchAgent finds them

---

### 5. List Agent 📝

**Role:** Manage lists (shopping, todos, etc)

**Operations:**
- `add_to_list(list_name, items)` → Add items
- `get_list(list_name)` → View list
- `check_item(item_id)` → Mark complete
- `remove_item(item_id)` → Remove

**List Types:**
- Shopping lists
- Todo lists
- Project lists
- Any categorized collection

**Integration with Memory:**
- Lists stored in memory
- Can search "What's on my shopping list?"

---

### 6. Search Agent (Retrieval Crew) 🔎

**Role:** Find information from your memory

**Operations:**
- `search(query, filters)` → Semantic search
- Returns: Relevant memories ranked by relevance

**Powers:**
- Vector search (semantic similarity)
- Metadata filtering (date, people, tags)
- Hybrid search (vector + keyword)

**Examples:**
- "What did María say about Barcelona?"
- "Tasks I have tomorrow"
- "When is Juan's birthday?"

---

### 7. Chat Agent 💬 (Future)

**Role:** Handle general conversation (non-memory related)

**Examples:**
- "What do you think about AI?"
- "Tell me a joke"
- "How's the weather?" (if we add weather API)

**Why separate?**
- Can use different LLM (cheaper for general chat)
- Can add personality/style
- Doesn't pollute memory with casual chat

---

## Data Flow Examples

### Example 1: Store Memory

```
User: "María me contó que se muda a Barcelona en marzo"
  ↓
Agent Zero:
  1. Intent Detection → MEMORY_STORE
  2. Extract: {
       content: "María se muda a Barcelona en marzo",
       people: ["María"],
       tags: ["mudanza", "Barcelona"]
     }
  3. Route to → MemoryAgent.store(...)
  4. MemoryAgent → Stores in vector DB
  5. Agent Zero → "Anotado! María se muda a Barcelona en marzo"
```

### Example 2: Query Memory

```
User: "¿Qué me contó María la semana pasada?"
  ↓
Agent Zero:
  1. Intent Detection → MEMORY_QUERY
  2. Route to → SearchAgent.search("María semana pasada")
  3. SearchAgent → Vector search + date filter
  4. Returns: [
       "María se muda a Barcelona en marzo",
       "María le gustan las flores"
     ]
  5. Agent Zero synthesizes → 
     "La semana pasada hablaste con María sobre:
     - Su mudanza a Barcelona en marzo
     - Le gustan las flores"
```

### Example 3: Create Task

```
User: "Recuérdame llamar a Juan mañana a las 3pm"
  ↓
Agent Zero:
  1. Intent Detection → TASK_CREATE
  2. Extract: {
       title: "llamar a Juan",
       due_at: "mañana 3pm"
     }
  3. Route to → TaskAgent.create_task(...)
  4. TaskAgent → Creates task in DB
  5. TaskAgent → ALSO stores in memory for context
  6. Agent Zero → "Te recordaré mañana a las 3pm llamar a Juan ✅"
```

### Example 4: Composite Intent

```
User: "Recuérdame llamar a Juan mañana. Ah, y guarda que le gusta el fútbol"
  ↓
Agent Zero:
  1. Intent Detection → COMPOSITE [TASK_CREATE, MEMORY_STORE]
  2. Parse into 2 actions:
     Action 1: {intent: TASK_CREATE, data: {...}}
     Action 2: {intent: MEMORY_STORE, data: {...}}
  3. Route to TaskAgent → Creates task
  4. Route to MemoryAgent → Stores note
  5. Agent Zero synthesizes →
     "Te recordaré mañana llamar a Juan. Y anotado que le gusta el fútbol ✅"
```

### Example 5: Context-Aware Query

```
User: "¿Qué sé sobre Juan?"
  ↓
Agent Zero:
  1. Intent Detection → MEMORY_QUERY
  2. Route to SearchAgent.search("Juan")
  3. SearchAgent finds:
     - Memory: "Juan le gusta el fútbol"
     - Task: "Llamar a Juan mañana"
     - List: "Comprar regalo para Juan"
  4. Agent Zero synthesizes →
     "Esto es lo que sé sobre Juan:
     
     💭 Notas:
     - Le gusta el fútbol
     
     ✅ Tareas:
     - Llamar a Juan (mañana)
     
     📝 Listas:
     - Comprar regalo para Juan (en tu lista de compras)"
```

---

## Agent Zero Implementation Details

### Core Loop

```python
class AgentZero:
    """
    Your personal AI assistant.
    Single personality that routes to specialized agents.
    """
    
    def __init__(self, llm, memory_service):
        self.llm = llm
        self.memory = memory_service
        
        # Specialized agents
        self.intent_detector = IntentDetector(llm)
        self.memory_agent = MemoryAgent(memory_service)
        self.task_agent = TaskAgent()
        self.list_agent = ListAgent()
        self.search_agent = SearchAgent(memory_service)
        
        # Conversation context
        self.contexts = {}  # {chat_id: [...messages]}
    
    async def handle_message(self, message, chat_id, user_id):
        """Main entry point for all messages."""
        
        # 1. Add to conversation context
        self._add_to_context(chat_id, "user", message)
        
        # 2. Detect intent
        intent_result = await self.intent_detector.detect(message)
        intent = intent_result["intent"]
        entities = intent_result["entities"]
        
        # 3. Route based on intent
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
        
        # 4. Generate natural response
        response = await self._synthesize_response(
            intent, result, message
        )
        
        # 5. Add to conversation context
        self._add_to_context(chat_id, "assistant", response)
        
        return response
    
    async def _handle_memory_store(self, entities, user_id):
        """Store new memory."""
        return await self.memory_agent.store(
            user_id=user_id,
            content=entities["content"],
            people=entities.get("people", []),
            tags=entities.get("tags", []),
            media=entities.get("media")
        )
    
    async def _handle_memory_query(self, entities, user_id):
        """Query memory."""
        query = entities["query"]
        
        # Use SearchAgent to find relevant memories
        results = await self.search_agent.search(
            query=query,
            user_id=user_id,
            filters=entities.get("filters", {})
        )
        
        return {
            "intent": "MEMORY_QUERY",
            "results": results,
            "query": query
        }
    
    async def _handle_task_create(self, entities, user_id, chat_id):
        """Create task (may need enrichment)."""
        
        # Check if we have all required fields
        missing = self._check_missing_fields("task", entities)
        
        if missing:
            # TaskAgent needs to ask for more info
            return await self.task_agent.enrich_and_create(
                user_id=user_id,
                initial_data=entities,
                ask_callback=lambda q: self._ask_user(chat_id, q)
            )
        
        else:
            # We have everything, create task
            return await self.task_agent.create_task(
                user_id=user_id,
                **entities
            )
    
    async def _handle_chat(self, message, user_id):
        """Handle general conversation."""
        
        # Get relevant context from memory
        context = await self.search_agent.search(
            query=message,
            user_id=user_id,
            limit=3
        )
        
        # Generate response with context
        prompt = f"""User: {message}

Context from their life:
{self._format_context(context)}

Respond naturally as their personal assistant."""
        
        response = self.llm.generate(prompt)
        
        return {
            "intent": "CHAT",
            "response": response
        }
    
    async def _synthesize_response(self, intent, result, original_message):
        """
        Generate natural language response.
        
        This is where Agent Zero's personality shines!
        """
        
        if intent == "MEMORY_STORE":
            return f"Anotado! {result['content']} ✅"
        
        elif intent == "MEMORY_QUERY":
            # Format search results naturally
            results = result["results"]
            if not results:
                return "No encontré nada sobre eso 🤔"
            
            # Let LLM format the results
            prompt = f"""User asked: {result['query']}

Found memories:
{self._format_results(results)}

Synthesize a natural response in Spanish."""
            
            return self.llm.generate(prompt)
        
        elif intent == "TASK_CREATE":
            task = result["task"]
            return f"Te recordaré {task['due_at']} {task['title']} ✅"
        
        elif intent == "LIST_ADD":
            items = result["items"]
            list_name = result["list_name"]
            return f"Añadido a {list_name}: {', '.join(items)} 📝"
        
        elif intent == "CHAT":
            return result["response"]
        
        # Default
        return "Hecho! ✅"
```

---

## Key Design Principles

### 1. **Single Personality**
- User only talks to Agent Zero
- Agents are invisible (user doesn't know they exist)
- Consistent voice throughout

### 2. **Memory-First**
- Everything stored in memory
- Agent Zero always has context
- Can answer "What do I know about X?"

### 3. **Extensible**
- Easy to add new agents (CalendarAgent, ContactAgent, etc)
- Easy to add new intents
- Easy to add new data types

### 4. **Natural Conversation**
- No rigid commands
- Multi-turn conversations
- Handles ambiguity (asks questions)
- Composite intents (multiple actions in one message)

### 5. **Smart Routing**
- Intent detector routes to right agent
- Agents can enrich data (ask questions)
- Agent Zero synthesizes final response

---

## Future Extensions

### Phase 2: Richer Data Types
```
- CalendarAgent (events, meetings)
- ContactAgent (people management)
- DocumentAgent (file storage, search)
- LocationAgent (places, addresses)
```

### Phase 3: Proactive Features
```
- Daily summary ("Here's what you have today")
- Suggestions ("You mentioned calling Juan, want a reminder?")
- Patterns ("You usually go to gym on Mondays")
```

### Phase 4: Integrations
```
- Google Calendar sync
- Email integration
- WhatsApp export
- Photo library
```

---

## Migration Path

### Step 1: Refactor Current Orchestrator
- Rename to AgentZero
- Keep intent detection
- Add routing logic
- Keep all existing agents

### Step 2: Upgrade Agents to Crews
- TaskAgent → TaskCrew (with enrichment)
- MemoryAgent → MemoryCrew (with summarization)
- ListAgent → ListCrew

### Step 3: Improve Memory
- Better vector search
- Metadata filtering
- Cross-referencing (link tasks to memories)

### Step 4: Add Chat Mode
- General conversation
- Context-aware responses
- Personality tuning

---

## Success Metrics

**You'll know it's working when:**

✅ You can ask: "What did I talk about with María?" and it finds the conversation

✅ You can say: "Recuérdame esto mañana" and it creates a task

✅ You can ask: "What do I have tomorrow?" and it shows tasks + events + context

✅ You can have normal conversations: "What do you think about this?" and it responds like ChatGPT but with YOUR context

✅ It feels like talking to someone who KNOWS your life

---

## The Big Picture

```
You want: ChatGPT + Your Life Knowledge

Current ChatGPT:
  "What did I tell you about María?" → "I don't have that information"

Your VitaeRules:
  "What did I tell you about María?" → "You told me:
    - She's moving to Barcelona in March
    - She likes flowers
    - You have a call scheduled with her tomorrow"
```

**That's the vision! 🎯**

Does this align with what you want? Should we implement this architecture?
