# Quick Fix Implementation Guide

Based on the flow analysis, here are the specific code changes to implement the optimizations.

## Phase 1: Quick Wins (Implement These First)

### Fix 1: Make list_name Optional in List Search Tool

**File:** `src/app/tools/list_search_tool.py`

**Current Issue:** `list_name` is required but should be optional

**Fix:**
```python
class ListSearchToolSchema(BaseModel):
    """Input schema for list search tool."""
    search_query: Optional[str] = Field(
        default=None,
        description="Keywords to search for in list names and item contents"
    )
    list_name: Optional[str] = Field(
        default=None,  # ADD THIS
        description="Optional: specific list name to search within. Leave empty to search all lists"
    )
```

---

### Fix 2: Add Array-to-Dict Extraction for Tool Inputs

**File:** `src/app/tools/task_search_tool.py`

**Current Issue:** LLM outputs arrays `[{...}, {...}]` instead of dict `{...}`

**Fix:**
```python
def _run(
    self,
    completed: Optional[bool] = None,
    search_query: Optional[str] = None,
    **kwargs,
) -> str:
    """Execute task search with the provided filters."""
    
    # ADD THIS BLOCK AT THE START:
    # Handle case where LLM outputs array instead of dict
    if isinstance(completed, list):
        self.tracer.warning(f"Received array for 'completed': {completed}, extracting first element")
        completed = completed[0] if len(completed) > 0 and isinstance(completed[0], (bool, type(None))) else None
    
    if isinstance(search_query, list):
        self.tracer.warning(f"Received array for 'search_query': {search_query}, extracting first element")
        search_query = search_query[0] if len(search_query) > 0 and isinstance(search_query[0], str) else None
    
    # EXISTING CODE CONTINUES...
    user_id = self.user_context.user_id
    if user_id is None:
        return "Error: User context is required for task search."
```

**File:** `src/app/tools/list_search_tool.py`

**Add same fix:**
```python
def _run(
    self,
    search_query: Optional[str] = None,
    list_name: Optional[str] = None,
    **kwargs,
) -> str:
    """Execute list search with the provided filters."""
    
    # ADD THIS BLOCK AT THE START:
    # Handle case where LLM outputs array instead of dict
    if isinstance(search_query, list):
        self.tracer.warning(f"Received array for 'search_query': {search_query}, extracting first element")
        search_query = search_query[0] if len(search_query) > 0 and isinstance(search_query[0], str) else None
    
    if isinstance(list_name, list):
        self.tracer.warning(f"Received array for 'list_name': {list_name}, extracting first element")
        list_name = list_name[0] if len(list_name) > 0 and isinstance(list_name[0], str) else None
    
    # EXISTING CODE CONTINUES...
    user_id = self.user_context.user_id
    if user_id is None:
        return "Error: User context is required for list search."
```

---

### Fix 3: Add Max Retry Limit to CrewAI Agents

**File:** `src/app/crews/search/search_flow.py` (or wherever agents are configured)

**Current Issue:** Agents retry indefinitely on tool failures

**Fix Option A - Per Agent:**
```python
# When creating agents, add max_iter parameter
task_searcher = Agent(
    role="Task Searcher",
    goal="Search for tasks...",
    backstory="...",
    tools=[task_search_tool],
    llm=llm,
    max_iter=5,  # ADD THIS - limits retries to 5 attempts
    verbose=verbose
)

list_searcher = Agent(
    role="List Searcher",
    goal="Search for lists...",
    backstory="...",
    tools=[list_tool],
    llm=llm,
    max_iter=5,  # ADD THIS
    verbose=verbose
)
```

**Fix Option B - Global Configuration:**
```python
# If using Crew-level configuration
crew = Crew(
    agents=[task_searcher, list_searcher, ...],
    tasks=[task_search_task, list_search_task, ...],
    max_rpm=None,
    max_iter=5,  # ADD THIS - applies to all agents
    verbose=verbose
)
```

---

## Phase 2: Conditional Search Execution

### Fix 4: Skip Low-Priority Searches When High-Priority Succeeds

**File:** `src/app/crews/search/search_flow.py`

**Current Issue:** All searches execute regardless of priority or previous results

**Implementation:**

```python
async def execute_searches(coordinator_result, user_context, tracer):
    """
    Execute searches based on coordinator strategy with conditional execution.
    Skips LOW/VERY LOW priority searches if HIGH priority search finds results.
    """
    results = {
        "memory": None,
        "tasks": None,
        "lists": None
    }
    
    # Helper function to check if results exist
    def has_results(search_result):
        if search_result is None:
            return False
        # Check if result has items (adjust based on your result structure)
        if isinstance(search_result, list):
            return len(search_result) > 0
        if isinstance(search_result, dict):
            return search_result.get('items') or search_result.get('results')
        return bool(search_result)
    
    # Helper function to determine if search should execute
    def should_execute(priority: str, high_priority_found: bool) -> bool:
        priority_lower = priority.lower()
        
        # Always execute HIGH and MEDIUM priority
        if priority_lower in ["high", "medium"]:
            return True
        
        # For LOW and VERY LOW, only execute if high priority found nothing
        if priority_lower in ["low", "very low"]:
            if high_priority_found:
                tracer.info(f"Skipping {priority} priority search - high priority search found results")
                return False
            return True
        
        # Default to executing
        return True
    
    # 1. Execute HIGH priority searches first
    high_priority_found = False
    
    if coordinator_result.memory.priority.lower() == "high":
        tracer.info("Executing HIGH priority: memory search")
        results["memory"] = await execute_memory_search(
            coordinator_result.memory.search_query,
            user_context,
            tracer
        )
        if has_results(results["memory"]):
            high_priority_found = True
    
    if coordinator_result.tasks.priority.lower() == "high":
        tracer.info("Executing HIGH priority: task search")
        results["tasks"] = await execute_task_search(
            coordinator_result.tasks.search_query,
            user_context,
            tracer
        )
        if has_results(results["tasks"]):
            high_priority_found = True
    
    if coordinator_result.lists.priority.lower() == "high":
        tracer.info("Executing HIGH priority: list search")
        results["lists"] = await execute_list_search(
            coordinator_result.lists.search_query,
            user_context,
            tracer
        )
        if has_results(results["lists"]):
            high_priority_found = True
    
    # 2. Execute MEDIUM priority searches
    if coordinator_result.memory.priority.lower() == "medium":
        tracer.info("Executing MEDIUM priority: memory search")
        results["memory"] = await execute_memory_search(
            coordinator_result.memory.search_query,
            user_context,
            tracer
        )
    
    if coordinator_result.tasks.priority.lower() == "medium":
        tracer.info("Executing MEDIUM priority: task search")
        results["tasks"] = await execute_task_search(
            coordinator_result.tasks.search_query,
            user_context,
            tracer
        )
    
    if coordinator_result.lists.priority.lower() == "medium":
        tracer.info("Executing MEDIUM priority: list search")
        results["lists"] = await execute_list_search(
            coordinator_result.lists.search_query,
            user_context,
            tracer
        )
    
    # 3. Execute LOW/VERY LOW priority searches ONLY if no high priority results
    if coordinator_result.memory.priority.lower() in ["low", "very low"]:
        if should_execute(coordinator_result.memory.priority, high_priority_found):
            tracer.info(f"Executing {coordinator_result.memory.priority} priority: memory search")
            results["memory"] = await execute_memory_search(
                coordinator_result.memory.search_query,
                user_context,
                tracer
            )
        else:
            tracer.info(f"Skipping memory search (priority: {coordinator_result.memory.priority})")
    
    if coordinator_result.tasks.priority.lower() in ["low", "very low"]:
        if should_execute(coordinator_result.tasks.priority, high_priority_found):
            tracer.info(f"Executing {coordinator_result.tasks.priority} priority: task search")
            results["tasks"] = await execute_task_search(
                coordinator_result.tasks.search_query,
                user_context,
                tracer
            )
        else:
            tracer.info(f"Skipping task search (priority: {coordinator_result.tasks.priority})")
    
    if coordinator_result.lists.priority.lower() in ["low", "very low"]:
        if should_execute(coordinator_result.lists.priority, high_priority_found):
            tracer.info(f"Executing {coordinator_result.lists.priority} priority: list search")
            results["lists"] = await execute_list_search(
                coordinator_result.lists.search_query,
                user_context,
                tracer
            )
        else:
            tracer.info(f"Skipping list search (priority: {coordinator_result.lists.priority})")
    
    return results
```

---

## Phase 3: Improve Agent Prompts

### Fix 5: Add Explicit Format Instructions to Agent Backstories

**File:** `src/app/crews/search/search_flow.py` (or agent definitions file)

**For Task Searcher Agent:**
```python
task_searcher = Agent(
    role="Task Searcher",
    goal="Search for tasks based on the coordinator's strategy.",
    backstory="""You are a specialized agent that searches for tasks and todos.
    
    CRITICAL FORMAT RULES:
    1. Output ONLY ONE tool call at a time
    2. NEVER output both Action and Final Answer together
    3. Use ONLY dictionary format: {"key": "value"}
    4. NEVER use array format: [{...}, {...}]
    5. Example CORRECT format:
       Action: task_search
       Action Input: {"completed": null, "search_query": "meeting"}
    6. Example INCORRECT format (DO NOT USE):
       Action Input: [{"completed": null, "search_query": "meeting"}, {"tasks": []}]
    
    If you encounter "Action Input is not a valid key, value dictionary" error:
    - You are likely outputting an array instead of a dict
    - Or you are trying to predict the tool's output
    - Only provide the INPUT to the tool, never the expected OUTPUT
    
    When searching:
    - Use the task_search tool with appropriate filters
    - completed: null (all tasks), true (completed only), false (incomplete only)
    - search_query: keywords to search for
    - If no results found, respond with "No tasks found matching the query"
    """,
    tools=[task_search_tool],
    llm=llm,
    max_iter=5,
    verbose=verbose
)
```

**For List Searcher Agent:**
```python
list_searcher = Agent(
    role="List Searcher",
    goal="Search for lists and list items based on the coordinator's strategy.",
    backstory="""You are a specialized agent that searches for lists and their items.
    
    CRITICAL FORMAT RULES:
    1. Output ONLY ONE tool call at a time
    2. Use ONLY dictionary format: {"key": "value"}
    3. NEVER use array format: [{...}, {...}]
    4. The 'list_name' parameter is OPTIONAL:
       - If you know the list name: {"search_query": "milk", "list_name": "Shopping"}
       - If you don't know: {"search_query": "milk", "list_name": null}
       - NEVER pass empty string: {"list_name": ""}
    
    When searching:
    - Use the list_search tool with appropriate parameters
    - search_query: keywords to search in list names and item contents
    - list_name: specific list to search (optional)
    - If no results found, respond with "No lists found matching the query"
    """,
    tools=[list_tool],
    llm=llm,
    max_iter=5,
    verbose=verbose
)
```

---

## Testing Checklist

After implementing these fixes, test with:

### Test 1: Simple Memory Query
```
Query: "Que edad tiene Olivia?"
Expected:
- Memory search: executes (HIGH priority)
- Task search: SKIPPED (LOW priority, memory found results)
- List search: SKIPPED (VERY LOW priority, memory found results)
- Response time: ~150-200s (vs 418s before)
- No tool errors
```

### Test 2: Task Query
```
Query: "What tasks do I have about Olivia?"
Expected:
- Task search: executes (HIGH priority)
- Memory search: executes (MEDIUM priority)
- List search: conditional
- No JSON parsing errors
- Response time: ~200-250s
```

### Test 3: No Results Query
```
Query: "What do I know about XYZ?" (where XYZ doesn't exist)
Expected:
- All HIGH priority searches execute
- LOW priority searches execute (since HIGH found nothing)
- Response: "I don't have that information"
- Response time: ~250-300s
```

---

## Deployment Steps

1. **Make fixes in order:**
   - Fix 1: list_name optional
   - Fix 2: array-to-dict extraction
   - Fix 3: max retry limit
   - Test on Windows first

2. **Commit and push:**
   ```bash
   git add src/app/tools/task_search_tool.py src/app/tools/list_search_tool.py
   git commit -m "fix: improve tool input handling and add retry limits"
   git push
   ```

3. **Deploy to Pi5:**
   ```bash
   # SSH to Pi5
   cd /config/VitaeRules
   git pull
   docker stop vitaerules
   docker rm vitaerules
   docker build -t vitaerules:latest .
   docker run -d --name vitaerules --restart unless-stopped --network host \
     -e APP_ENV=prod -e OLLAMA_BASE_URL=http://localhost:11434 \
     -v vitae_data:/app/data vitaerules:latest
   ```

4. **Monitor logs:**
   ```bash
   docker logs -f vitaerules
   ```

5. **Test same queries and compare:**
   - Response times
   - Error frequency
   - Answer accuracy

---

## Expected Impact

### Before:
- Query time: ~418s (7 minutes)
- Tool failures: 40%
- Unnecessary executions: 60%

### After Phase 1:
- Query time: ~418s (same - but cleaner logs)
- Tool failures: <5%
- Unnecessary executions: 60% (same)

### After Phase 2:
- Query time: ~150-200s (50% faster)
- Tool failures: <5%
- Unnecessary executions: <10%

### After Phase 3:
- Query time: ~150-200s
- Tool failures: <2%
- Unnecessary executions: <5%
