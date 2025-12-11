# Binary SEARCH/ACTION Architecture Implementation

**Date:** October 30, 2025  
**Status:** ✅ IMPLEMENTED

## Summary

Successfully transformed the bot from a 3-way intent system (CHAT/SEARCH/ACTION) to a binary system (SEARCH/ACTION) to align with the app's core purpose: storing and querying memories.

---

## Changes Implemented

### 1. **ConversationIntent Enum** (`src/app/crews/chat/crew.py`)

**Before:**
```python
class ConversationIntent(str, Enum):
    CHAT = "chat"      # General conversation
    SEARCH = "search"  # Search for information
    ACTION = "action"  # Execute an action
```

**After:**
```python
class ConversationIntent(str, Enum):
    """Binary classification:
    - SEARCH: Retrieve/query existing information
    - ACTION: Store/modify data or communicate (default)
    """
    SEARCH = "search"  # Search for stored information
    ACTION = "action"  # Execute an action or store data (default)
```

---

### 2. **Intent Detection Prompt** (`src/app/crews/chat/crew.py`)

**Key Changes:**
- Removed CHAT category entirely
- Binary classification: SEARCH vs ACTION
- Default to ACTION when unclear
- Clear examples for both categories
- Emphasis on question words for SEARCH
- Emphasis on statements/commands for ACTION

**SEARCH indicators:**
- Question words: What, When, Where, Who, How, Why, Do, Does, Did, Is, Are
- Queries about stored data
- General knowledge questions

**ACTION indicators (default):**
- Statements with information
- Commands to store/modify data
- Social interactions (greetings, thanks)
- Responses providing information
- When in doubt

---

### 3. **Intent Parsing Logic** (`src/app/crews/chat/crew.py`)

**Before:** 3-way classification with CHAT as fallback

**After:** Binary classification with ACTION as default
```python
# Check for SEARCH (more specific)
if "SEARCH" detected:
    intent = ConversationIntent.SEARCH
else:
    # Default to ACTION
    intent = ConversationIntent.ACTION
```

---

### 4. **Task Descriptions** (`src/app/crews/chat/crew.py`)

**Updated:**
- Removed "If CHAT:" branches from task descriptions
- Kept only SEARCH and ACTION handling
- Updated expected behaviors for binary system

---

### 5. **CaptureCrew Planning** (`src/app/crews/capture/crew.py`)

**Enhanced Planner Task:**
- Explicitly check if message contains valuable information
- Greetings/trivial messages → `actions: []` (empty)
- Information with entities → populate actions list
- Planner decides what's worth storing

**Key Logic:**
```
Trivial message ("Hello", "Thanks")
  → actions: []
  → No storage
  → Just respond conversationally

Valuable message (entities, events)
  → actions: [memory_note_tool, ...]
  → Execute tools
  → Save to LTM
```

---

### 6. **CaptureCrew Execution** (`src/app/crews/capture/crew.py`)

**Enhanced Execution Task:**
- Check if actions list is empty
- Empty actions → provide conversational response only
- Non-empty actions → execute tools and save

**Examples:**
- "Hello" → actions=[] → "Hello! How can I help?"
- "Hoy fuimos con Biel" → actions=[memory_note_tool] → Save and confirm

---

### 7. **SearchCrew LLM Fallback** (`src/app/crews/search/crew.py`)

**Enhanced Aggregation Task:**

**When results found:**
- Deduplicate, rank, format
- Present findings naturally

**When NO results found:**
- **General knowledge question** → Answer from LLM knowledge
  - Example: "Who built Sagrada Familia?" → "Antoni Gaudí designed..."
  
- **Personal/unknown question** → Ask for clarification
  - Example: "What's my cat's name?" → "I don't have that information. Can you tell me?"
  - Allows conversation to continue → User provides info → Triggers ACTION

---

## Architecture Flow

### **SEARCH Intent:**
```
User: "What is in my shopping list?"
  ↓
SEARCH intent detected
  ↓
SearchCrew searches LTM
  ↓
├─ FOUND: Present results
│  "Your shopping list has: milk, eggs, bread"
│
└─ NOT FOUND: Check question type
    ├─ General knowledge: Answer from LLM
    │  "Sagrada Familia was designed by Gaudí..."
    │
    └─ Personal/unknown: Ask for details
       "I don't have that information. Can you tell me?"
       → User provides info → ACTION triggered
```

### **ACTION Intent:**
```
User: "Hoy fuimos a la oficina con Biel"
  ↓
ACTION intent detected (default)
  ↓
CaptureCrew activates
  ↓
Planner extracts:
  - entities: {people: [Biel], location: [office], event: [visit]}
  - actions: [memory_note_tool]
  ↓
Clarifier (if needed): Ask for missing info
  ↓
Tool Executor: Execute tools
  ↓
Summarize session: "Office visit with Biel on [date]"
  ↓
Save to LTM
  ↓
Confirm: "I've noted your office visit with Biel"
```

### **Trivial Message:**
```
User: "Hello"
  ↓
ACTION intent (default)
  ↓
CaptureCrew activates
  ↓
Planner: No entities, trivial message
  - actions: []
  ↓
Tool Executor: No actions to execute
  - Generate conversational response
  ↓
Response: "Hello! How can I help you today?"
  ↓
Nothing saved (no storage overhead)
```

---

## Key Benefits

1. **✅ Purpose-aligned:** Everything is stored by default (aligns with memory-first design)
2. **✅ Simpler classification:** Binary choice easier for LLM than 3-way
3. **✅ No information loss:** Valuable info automatically captured
4. **✅ Session-aware:** Multi-turn conversations accumulate naturally
5. **✅ Smart about trivial messages:** No storage overhead for greetings
6. **✅ LLM fallback:** General knowledge questions answered gracefully
7. **✅ Clarification flow:** Personal unknowns lead to information gathering

---

## Testing Plan

### Test Case 1: Greeting (Trivial Message)
```
Input: "Hello"
Expected:
  - Intent: ACTION
  - Planner: actions=[]
  - Response: "Hello! How can I help?"
  - Storage: None
```

### Test Case 2: Statement with Information
```
Input: "Hoy fuimos a la oficina con Biel"
Expected:
  - Intent: ACTION
  - Planner: actions=[memory_note_tool]
  - Entities: {people: [Biel], location: [office]}
  - Storage: Memory note created
  - Response: Confirmation
```

### Test Case 3: Question about Stored Data
```
Input: "What is in my shopping list?"
Expected:
  - Intent: SEARCH
  - Search: Query list_tool
  - Results: List contents or "No list found"
```

### Test Case 4: General Knowledge Question
```
Input: "Who built Sagrada Familia?"
Expected:
  - Intent: SEARCH
  - Search: No personal data found
  - LLM: Answer from general knowledge
  - Response: "Antoni Gaudí designed..."
```

### Test Case 5: Personal Unknown Question
```
Input: "What is my cat's name?"
Expected:
  - Intent: SEARCH
  - Search: No results
  - Response: "I don't have that information. Can you tell me?"
  - Session continues...

Follow-up: "Her name is Luna"
Expected:
  - Intent: ACTION (session continues)
  - Planner: Sees full STM context (question + answer)
  - actions=[memory_note_tool]
  - Storage: "User's cat: Luna"
```

### Test Case 6: Multi-turn Session
```
Turn 1: "Hello"
  → ACTION, actions=[], no storage
  
Turn 2: "I went to the office today"
  → ACTION, actions=[memory_note_tool]
  → STM accumulates
  
Turn 3: "With Biel"
  → ACTION continues session
  → Planner sees full context
  → Summarize: "Office visit with Biel on [date]"
  → Save to LTM
```

---

## Next Steps

1. ✅ Implementation complete
2. ⏳ Test binary intent detection with various messages
3. ⏳ Test ACTION tool execution (verify tools run, not simulated)
4. ⏳ Test multi-turn session accumulation
5. ⏳ Monitor performance and optimize if needed

---

## Files Modified

1. `src/app/crews/chat/crew.py`
   - ConversationIntent enum (removed CHAT)
   - Intent detection prompt (binary)
   - Intent parsing logic (default to ACTION)
   - Task descriptions (removed CHAT branches)

2. `src/app/crews/capture/crew.py`
   - Planning task (check for trivial messages)
   - Execution task (handle empty actions)

3. `src/app/crews/search/crew.py`
   - Aggregation task (LLM fallback logic)

---

## Performance Considerations

**Current:**
- SEARCH: ~2-3 minutes (SearchCrew complexity)
- ACTION: ~5 minutes (CaptureCrew with 3 agents)

**Optimization opportunities:**
- Use faster LLM for classification/planning
- Parallelize independent tasks
- Cache common queries
- Simplify crew structures

**Trade-off accepted:**
- Slightly slower responses
- But: No information loss + Better memory capture
