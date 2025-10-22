# Planner Validation Error Fix

## 🐛 Issue Identified

**Error Message:**
```
ValidationError: 2 validation errors for Plan
intent
  Input should be 'task.create', 'task.complete', ..., 'memory.note', ... [type=enum, input_value='memory.note|task.create', input_type=str]
followups.0.ask
  Field required [type=missing, input_value={'question': 'What is the...', 'required': True}, input_type=dict]
```

**Root Causes:**

1. **Invalid Intent Format**: LLM generated `'memory.note|task.create'` (combined with pipe `|`)
   - Expected: Single value like `'memory.note'`
   - LLM was confused by the example format showing multiple options with `|`

2. **Wrong Followup Field Name**: LLM generated `'question'` field
   - Expected: `'ask'` field
   - Example in prompt used `'question'` instead of `'ask'`

## ✅ Fixes Applied

### 1. Updated Prompt Structure (planner.py)

**Before:**
```python
{{
    "intent": "memory.note|memory.query|task.create|...",  # ❌ Confusing!
    "followups": [
        {{"question": "What is...?", "field": "due_date", "required": true}}  # ❌ Wrong field!
    ],
    ...
}}
```

**After:**
```python
{{
    "intent": "memory.note",  # ✅ Clear single value
    "followups": [
        {{"ask": "What is...?", "field": "due_date"}}  # ✅ Correct field
    ],
    ...
}}
```

### 2. Added Explicit Rules

```
CRITICAL RULES:
1. "intent" MUST be ONE value from: task.create, ..., memory.note, ...
2. NEVER use pipe "|" or combine multiple intents - choose PRIMARY intent only
3. Followup format: {"ask": "question text", "field": "field_name"} (use "ask" not "question")
...
```

### 3. Enhanced System Prompt

Added explicit warnings to the system prompt:

```python
system_prompt = """...
CRITICAL: 
- The "intent" field must be EXACTLY ONE value (like "memory.note"), never combine with "|"
- The "followups" field must use "ask" not "question"
- All enum values must match exactly as specified in the prompt"""
```

## 🧪 Verification

**Test Input:**
```
"Hola! Hoy hemos recibido el ingreso de la subvencion"
```

**Result:**
```
Intent: memory.note          ✅ Single value
Actions: 1                   ✅ Valid action
Confidence: 0.9              ✅ High confidence
```

## 📊 Impact

### Before Fix
- ❌ LLM generated invalid JSON that failed Pydantic validation
- ❌ Fell back to 30% confidence fallback plan
- ⚠️ Still worked but with degraded quality

### After Fix
- ✅ LLM generates valid JSON on first attempt
- ✅ Proper 90% confidence plans
- ✅ No validation errors
- ✅ Cleaner error logs

## 🔍 Key Learnings

1. **Be Explicit with Enums**: Show ONE example value, not a list with `|`
2. **Match Field Names Exactly**: If schema expects `ask`, use `ask` in examples
3. **Add Defensive Rules**: Explicit "NEVER do X" rules help LLMs avoid mistakes
4. **System Prompt Matters**: Critical constraints should be in both user prompt AND system prompt

## 📝 Files Modified

- `src/app/crews/capture/planner.py`
  - Updated `_build_planning_prompt()` example structure
  - Added CRITICAL RULES section
  - Enhanced system prompt with explicit warnings

## ✅ Status

- **Fixed**: Intent validation error
- **Fixed**: Followup field name error  
- **Fixed**: Safety check blocking normal operations
- **Verified**: Planner generates valid JSON
- **Tested**: Same input that caused original error now works correctly

---

## 🐛 Additional Issue Fixed (Oct 22, 2025)

### Problem: Safety Check Blocking Memory Notes

**Error:**
```
tool_caller.blocked
Plan blocked: Memory note creation is non-urgent
```

**Root Cause:**
LLM was incorrectly setting `safety.blocked = true` for normal memory note operations, treating "non-urgent" items as something to block.

**Fix:**
Enhanced safety guidance in both user prompt and system prompt:

```python
# User Prompt - Added explicit rule:
11. SAFETY: Set "blocked": false for ALL normal operations (notes, tasks, lists, reminders)
    - ONLY set "blocked": true for truly dangerous operations
    - Creating notes, tasks, reminders is SAFE - never block these!
    - "non-urgent" is NOT a reason to block - user wants to save the information

# System Prompt - Added:
- SAFETY: Always set "blocked": false for normal operations
  - NEVER block memory notes, tasks, or reminders - these are safe operations!
  - ONLY block truly dangerous operations (delete all data, harmful content)
```

**Result:**
```
Safety blocked: False ✅
Safety reason: Memory note about a subsidy - safe operation ✅
```

Memory notes and other normal operations now execute successfully!

---

*Fixed on: October 22, 2025*
*The planner now generates 90% confidence plans instead of falling back to 30% confidence defaults! 🎉*
*Safety checks no longer incorrectly block normal operations! 🔓*
