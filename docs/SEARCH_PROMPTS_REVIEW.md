# Search Execution Prompts - Complete View

## 🔍 All Prompts Used in SearchCrew (Phase 2)

**File**: `src/app/crews/search/crew.py`

---

## 1. 🎯 Search Coordinator Agent

### Agent Configuration:
**File**: `src/app/crews/search/coordinator.py`

```python
role: "Search Coordinator"

goal: "Analyze search queries to determine which data sources to search 
       (memory, tasks, lists) and how to combine results effectively"

backstory: "You are an expert at understanding search intent and determining 
            the best data sources to query. You analyze queries to identify 
            if the user is looking for: memories/notes (use memory search), 
            tasks/reminders (use task search), lists/items (use list search), 
            or a combination. You consider keywords like 'remember', 'task', 
            'todo', 'list', 'shopping' to determine intent. You're strategic 
            about which sources will yield the best results without unnecessary 
            searches."
```

⚠️ **Issue**: Contains keyword list ("remember", "task", "todo", "list", "shopping")

---

### Task Prompt:

```
Analyze this search query and determine the best search strategy:

Query: "{query}"
Available sources: {sources_str}

Determine:
1. Which sources are most relevant to this query?
   - Memory: for notes, diary entries, stored information
   - Tasks: for todos, reminders, scheduled items
   - Lists: for list items, shopping lists, collections

2. What are the key search terms and entities?
   - People mentioned
   - Dates/times referenced
   - Topics or keywords

3. How should results be prioritized?

Output a search strategy with recommended sources and search criteria.
```

**Expected Output**: "Search strategy with recommended sources and criteria"

**Time**: ~12-15s

---

## 2. 💾 Memory Searcher Agent

### Agent Configuration:
**File**: `src/app/crews/search/memory_searcher.py`

```python
role: "Memory Searcher"

goal: "Search long-term memory for relevant notes, diary entries, and stored information"

backstory: "You are an expert at searching through memories and notes to find 
            relevant information. You understand how to use vector similarity search 
            and can filter results by people, dates, locations, and tags. You rank 
            results by relevance and recency."
```

✅ **Good**: No keywords in backstory

---

### Task Prompt:

```
Search long-term memory based on the coordinator's strategy:

Query: "{query}"

Use the search criteria from the coordinator to:
1. Search memory with appropriate filters (people, dates, tags)
2. Retrieve relevant memories ranked by similarity
3. Include metadata (timestamps, people, locations, tags)

Return the top matching memories with their details.
```

**Context**: Has access to `coordination_task` output  
**Expected Output**: "List of relevant memories with metadata"  
**Time**: ~12s  
**Issue**: ❌ Should check coordinator's recommendation before searching

---

## 3. ✅ Task Searcher Agent

### Agent Configuration:
**File**: `src/app/crews/search/task_searcher.py`

```python
role: "Task Searcher"

goal: "Search tasks and reminders to find relevant todos and scheduled items"

backstory: "You are an expert at searching through tasks and reminders. You 
            understand how to filter by status, due date, priority, and content. 
            You rank results by relevance, urgency, and due date proximity."
```

✅ **Good**: No keywords in backstory

---

### Task Prompt:

```
Search tasks and reminders based on the coordinator's strategy:

Query: "{query}"

Use the search criteria from the coordinator to:
1. Search tasks with appropriate filters (status, due date, priority)
2. Retrieve relevant tasks ranked by relevance
3. Include metadata (title, due date, priority, status, description)

Return the top matching tasks with their details.
```

**Context**: Has access to `coordination_task` output  
**Expected Output**: "List of relevant tasks with metadata"  
**Time**: ~12s  
**Issue**: ❌ Should check coordinator's recommendation before searching

---

## 4. 📋 List Searcher Agent

### Agent Configuration:
**File**: `src/app/crews/search/list_searcher.py`

```python
role: "List Searcher"

goal: "Search lists and list items to find collections, shopping lists, and organized data"

backstory: "You are an expert at searching through lists and list items. You 
            understand list structures and can find relevant items across multiple 
            lists. You rank results by relevance and list context."
```

✅ **Good**: No keywords in backstory

---

### Task Prompt:

```
Search lists and list items based on the coordinator's strategy:

Query: "{query}"

Use the search criteria from the coordinator to:
1. Search list names and item contents
2. Retrieve relevant items with their list context
3. Include metadata (list name, position, status, tags, location)

Return the top matching list items grouped by list.
```

**Context**: Has access to `coordination_task` output  
**Expected Output**: "List of relevant list items grouped by list"  
**Time**: ~12s  
**Issue**: ❌ Should check coordinator's recommendation before searching

---

## 5. 📊 Result Aggregator Agent

### Agent Configuration:
**File**: `src/app/crews/search/aggregator.py`

```python
role: "Result Aggregator"

goal: "Combine search results from multiple sources into a unified, user-friendly response"

backstory: "You are an expert at synthesizing information from multiple sources. 
            You deduplicate results, rank by relevance, and format information 
            clearly for users. When no results are found, you determine if the 
            question is general knowledge (which you can answer) or personal 
            (which requires more information)."
```

✅ **Good**: No keywords, clear semantic description

---

### Task Prompt:

```
Combine search results from all sources into a unified response:

Original query: "{query}"

Using results from previous tasks:

IF RESULTS WERE FOUND (memories, tasks, or lists):
1. Deduplicate similar results across sources
2. Rank all results by relevance to the original query
3. Format into a clear, user-friendly response
4. Provide:
   - Summary of what was found (counts by source type)
   - Top results from each source with context
   - Overall relevance score or recommendation

IF NO RESULTS WERE FOUND in any source:
1. Determine if this is a general knowledge question or personal question
2. General knowledge questions (e.g., "Who built Sagrada Familia?", "What is 2+2?"):
   - Try to answer using your general knowledge
   - Provide a helpful, informative answer
   - Example: "The Sagrada Familia was designed by Antoni Gaudí..."
3. Personal questions you cannot answer (e.g., "What's my cat's name?", "When is my appointment?"):
   - Respond: "I don't have that information. Can you provide more details?"
   - This allows the conversation to continue and collect the information

Make the response concise but informative.
```

**Context**: Has access to ALL previous task outputs  
**Expected Output**: "Unified search results summary with all findings, or general knowledge answer, or request for clarification"  
**Time**: ~15-20s  
⚠️ **Issue**: Contains examples ("Who built Sagrada Familia?", "What is 2+2?", "What's my cat's name?")

---

## 📊 Summary of Issues

### High Priority Issues:

1. **Search Coordinator Agent Backstory** ⚠️
   ```python
   "You consider keywords like 'remember', 'task', 'todo', 'list', 'shopping' 
   to determine intent."
   ```
   **Impact**: Encourages keyword matching instead of semantic understanding

2. **No Conditional Execution** ❌
   - Searchers always run, even when coordinator says "LOW RELEVANCE"
   - Wastes ~36-48 seconds on unnecessary searches
   - **Critical workflow issue**

3. **Result Aggregator Has Examples** ⚠️
   ```python
   2. General knowledge questions (e.g., "Who built Sagrada Familia?", "What is 2+2?"):
      - Example: "The Sagrada Familia was designed by Antoni Gaudí..."
   3. Personal questions (e.g., "What's my cat's name?", "When is my appointment?"):
   ```
   **Impact**: Potential keyword matching on examples

---

## 🔄 Example from Last Execution

### Query: "Hola, puedes detallar en que me puedes ayudar?"

**Coordinator Output** (LLM #2):
```
**Source Relevance Assessment:**
- Memory: LOW RELEVANCE (not asking for stored notes/diary)
- Tasks: LOW RELEVANCE (not requesting todos/reminders)
- Lists: LOW RELEVANCE (not seeking list items)

**Recommendation**: Direct response explaining capabilities rather than 
searching personal data sources.
```

**Memory Searcher** (LLM #3): ❌ Ran anyway
- Searched vector DB for: "ayudar", "detallar"
- Found: 0 results
- Time wasted: ~12s

**Task Searcher** (LLM #4): ❌ Ran anyway
- Searched SQL for: "ayudar", capability-related
- Found: 0 results
- Time wasted: ~12s

**List Searcher** (LLM #5): ❌ Ran anyway
- Searched SQL for: "ayudar", "detallar"
- Found: 0 results
- Time wasted: ~12s

**Result Aggregator** (LLM #6): ✅ Finally used fallback
- Saw: No results from any source
- Applied: General knowledge fallback
- Generated: Capability explanation in Spanish
- Time: ~15s

**Total Phase 2 Time**: ~68 seconds  
**Wasted Time**: ~36 seconds (3 unnecessary searches)

---

## 💡 Optimization Opportunities

### 1. Remove Keywords from Coordinator Backstory

**Current**:
```python
"You consider keywords like 'remember', 'task', 'todo', 'list', 'shopping' 
to determine intent."
```

**Proposed**:
```python
"You analyze the semantic meaning of queries to determine which data sources 
will yield relevant results. You're strategic about recommending only searches 
that will provide value to the user."
```

---

### 2. Make Searchers Respect Coordinator Recommendations

**Current**: All searchers always run

**Proposed Option A** - Self-aware searchers:
```python
memory_search_task = Task(
    description=f"""FIRST, check the coordinator's recommendation for Memory search.

IF coordinator says "Memory: LOW RELEVANCE" or "SKIP Memory":
    Output: "SKIPPED - Coordinator determined memory search not needed"
    
ELSE, search long-term memory:
    Query: "{query}"
    Use the coordinator's search criteria...
    Return matching memories with details.
""",
    agent=memory_searcher_agent,
    context=[coordination_task]
)
```

**Proposed Option B** - Dynamic task creation:
```python
# Parse coordinator output
coordinator_result = coordination_task.execute()
should_search_memory = "HIGH" in coordinator_result or "MEDIUM" in coordinator_result

# Only create search tasks for relevant sources
tasks = [coordination_task]
if should_search_memory:
    tasks.append(memory_search_task)
# ... etc

tasks.append(aggregation_task)
crew.tasks = tasks
```

**Time Savings**: ~36-48 seconds when searches aren't needed

---

### 3. Remove Examples from Aggregator Prompt

**Current**:
```python
2. General knowledge questions (e.g., "Who built Sagrada Familia?", "What is 2+2?"):
   - Example: "The Sagrada Familia was designed by Antoni Gaudí..."
```

**Proposed**:
```python
2. General knowledge questions:
   - Answer using your general knowledge
   - Provide helpful, informative responses
```

**Benefit**: More semantic, less pattern-matching

---

## 📈 Estimated Impact of All Optimizations

### Current Search Phase:
- Time: ~68 seconds
- LLM Calls: 5 (coordinator + 3 searchers + aggregator)
- Wasted effort: ~36 seconds on unnecessary searches

### Optimized Search Phase:
- Time: ~27 seconds (for "capability inquiry" type queries)
  - Coordinator: ~12s
  - Result Aggregator: ~15s (direct answer)
  - Skip all 3 searchers
  
- Time: ~55 seconds (for actual data queries)
  - Coordinator: ~12s
  - Relevant searchers only: ~12-36s (1-3 sources)
  - Result Aggregator: ~15s

**Improvement**: 40-60% faster depending on query type

---

## 🎯 Priority Ranking

1. **CRITICAL**: Implement conditional search execution (40-60% time savings)
2. **HIGH**: Remove keywords from Coordinator backstory (better semantic analysis)
3. **MEDIUM**: Remove examples from Aggregator prompt (consistency with intent prompt)

---

## ✅ What Works Well

1. **Clear task structure** - Each agent has well-defined responsibility
2. **Context passing** - Searchers get coordinator's strategy
3. **LLM fallback** - Aggregator handles "no results" gracefully
4. **Metadata requests** - Prompts ask for structured data
5. **Most agents** - 4/5 have clean, semantic backstories

---

## 🔄 Next Steps

Would you like me to:
1. **Remove keywords** from Search Coordinator backstory?
2. **Remove examples** from Result Aggregator prompt?
3. **Implement conditional execution** (respect coordinator recommendations)?
4. **Test optimized search** with actual queries?

The biggest impact would be #3 (conditional execution), but #1 and #2 are quick wins for consistency.
