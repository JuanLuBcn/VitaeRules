# Enrichment Testing Guide

## Is Enrichment Working?

### Quick Test

Send this message to the bot:
```
Remind me to call mom
```

**Expected Behavior with Enrichment**:
```
Bot: ✅ Perfecto, crearé la tarea: **Call mom**

     📅 ¿Cuándo quieres que te lo recuerde?
     💡 Por ejemplo: "mañana a las 9", "el viernes", "en 2 horas"
```

**Current Behavior (without enrichment)**:
```
Bot: ✅ Tarea creada: Call mom
```

If you're NOT seeing the follow-up question, enrichment is disabled or not working.

---

## Why Enrichment Might Not Be Working

### Possibility 1: Enrichment Disabled in Config
Check `.env` for:
```
ENABLE_ENRICHMENT=false  # If this exists and is false
```

### Possibility 2: Agent Returns Wrong Type
The agents need to return `AgentResponse` with `needs_enrichment=True`, but might be returning `AgentResult` instead.

### Possibility 3: Orchestrator Not Handling AgentResponse
The orchestrator checks for `isinstance(result, AgentResponse)` but the agent might be wrapping it incorrectly.

---

## What's In The Logs?

When you send "Remind me to call mom", check the logs for:

```powershell
Get-Content data/trace.jsonl -Tail 30 | Select-String "enrichment|AgentResponse"
```

**Look for**:
- ✅ `"needs_enrichment": true` - Enrichment was requested
- ✅ `"enrichment_started"` - Enrichment conversation began
- ✅ `"enrichment_question"` - Question was generated
- ❌ None of the above - Enrichment not triggered

---

## Current Code Status

### TaskAgent Returns AgentResponse ✅
```python
# In task_agent.py line 183:
return AgentResponse(
    message=preview,
    success=True,
    needs_enrichment=True,  # ✅ This is set!
    extracted_data=extracted_data,
    operation="create_task",
)
```

### Orchestrator Checks for AgentResponse ✅
```python
# In orchestrator.py line 129:
if isinstance(result, AgentResponse) and result.needs_enrichment:
    return await self._handle_enrichment_start(
        result, intent, chat_id, user_id
    )
```

### But... Type Mismatch Issue ⚠️
```python
# TaskAgent.handle() return type says:
async def handle(...) -> AgentResult:  # ❌ Wrong type annotation
    ...
    return await self._handle_create(...)  # Returns AgentResponse

# This should be:
async def handle(...) -> AgentResult | AgentResponse:
```

---

## The Fix

The issue is likely that Python's type system doesn't enforce runtime types, but the `handle()` method might be doing something that converts `AgentResponse` to `AgentResult`.

Let me check the actual execution flow...

---

## Debugging Steps

### Step 1: Add Debug Logging
Edit `src/app/agents/orchestrator.py` around line 125:

```python
result = await agent.handle(processing_message, chat_id, user_id, context=context)

# ADD THIS:
self.tracer.info(f"Agent result type: {type(result).__name__}")
self.tracer.info(f"Is AgentResponse: {isinstance(result, AgentResponse)}")
if hasattr(result, 'needs_enrichment'):
    self.tracer.info(f"needs_enrichment: {result.needs_enrichment}")
```

### Step 2: Restart Bot
```powershell
$env:PYTHONPATH="src"; python -m app.main
```

### Step 3: Send Test Message
```
Remind me to call mom
```

### Step 4: Check Logs
```powershell
Get-Content data/trace.jsonl -Tail 10
```

**Look for**:
```json
{"level": "INFO", "message": "Agent result type: AgentResponse"}
{"level": "INFO", "message": "Is AgentResponse: True"}
{"level": "INFO", "message": "needs_enrichment: True"}
```

If you see `AgentResult` instead of `AgentResponse`, then the conversion is happening somewhere.

---

## Possible Root Causes

### Cause 1: BaseAgent Wrapper
The `BaseAgent` base class might be wrapping the result.

**Check**: `src/app/agents/base.py`

### Cause 2: Return Type Coercion
Python might be type-checking and converting.

**Check**: No type guards in the code

### Cause 3: Inheritance Issue
`TaskAgent` might override something incorrectly.

**Check**: Class definition

---

## Quick Workaround Test

To test if enrichment works at all, try forcing it:

### Edit orchestrator.py temporarily:
```python
# Around line 125, replace:
result = await agent.handle(processing_message, chat_id, user_id, context=context)

# With:
result = await agent.handle(processing_message, chat_id, user_id, context=context)

# Force enrichment for testing:
if intent == IntentType.TASK and "create" in processing_message.lower():
    # Manually create AgentResponse
    from app.agents.enrichment_types import AgentResponse
    result = AgentResponse(
        message="✅ Creating task...",
        success=True,
        needs_enrichment=True,
        extracted_data={"title": "Test", "user_id": user_id},
        operation="create_task"
    )
```

If enrichment works with this forced response, the issue is in how `TaskAgent.handle()` returns the result.

---

## Expected Flow (If Working)

```
1. User: "Remind me to call mom"

2. Orchestrator: Classifies as TASK intent
   → Routes to TaskAgent

3. TaskAgent._handle_create():
   → Returns AgentResponse(needs_enrichment=True)

4. Orchestrator detects needs_enrichment
   → Calls _handle_enrichment_start()

5. EnrichmentAgent analyzes data:
   → Missing: due_at (when?)
   → Generates question

6. Bot: "📅 ¿Cuándo quieres que te lo recuerde?"

7. User: "Tomorrow at 9am"

8. Orchestrator: In enrichment mode
   → Routes to _handle_enrichment_response()

9. EnrichmentAgent extracts: due_at = "tomorrow 9am"
   → Returns completed enrichment

10. Orchestrator: Executes task creation
    → With enriched data

11. Bot: "✅ Creé la tarea 'Call mom' para mañana a las 9am"
```

---

## What To Tell Me

After testing, please share:

1. **What message did you send?**
   - Example: "Remind me to call mom"

2. **What response did you get?**
   - Immediate task creation?
   - Or follow-up question?

3. **Check logs** (last 30 lines):
   ```powershell
   Get-Content data/trace.jsonl -Tail 30
   ```

4. **Look for these keywords**:
   - `enrichment`
   - `AgentResponse`
   - `needs_enrichment`
   - `Agent result type`

This will help me pinpoint exactly where the enrichment flow is breaking!

---

## Summary

**Enrichment SHOULD work** based on the code, but:
- ⚠️ Type annotation mismatch in `TaskAgent.handle()`
- ⚠️ Need to verify actual runtime type of returned object
- ⚠️ Possible conversion happening somewhere

**To verify**: Add debug logging and share the output!
