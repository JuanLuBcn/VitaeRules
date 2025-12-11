# CaptureCrew Tool Execution Issue - Investigation Report
Date: November 2, 2025

## PROBLEM STATEMENT

When a user sends information to be stored (ACTION intent), CaptureCrew fails to execute the memory_note_tool. Instead, the Tool Executor agent returns a confusing message asking for clarification about what actions to execute, even though the plan clearly identifies actions needed.

**Error Log:**
```
2025-11-02 13:15:35 | ERROR | vitaerules | capture.memory_error
```

**Symptom:** Bot claims "He guardado todos los detalles" (I saved all the details) but no memory is actually created in the database.

---

## INVESTIGATION FINDINGS

### 1. Architecture Overview

**Flow:**
```
User Input → ChatCrew (Intent Detection) → CaptureCrew → CrewAI Orchestration
                ↓ ACTION intent
         CaptureCrew.capture_with_crew_tasks()
                ↓
         CrewAI with 3 agents:
         1. Planner → creates structured plan
         2. Clarifier → asks questions if needed
         3. Tool Executor → executes actions
```

### 2. Root Cause Analysis

#### **Issue #1: CrewAI Orchestration vs Direct Execution**

The CaptureCrew has **TWO different methods**:

**Method A: `capture()` - WORKING (Direct Execution)**
- Location: `crew.py` lines 156-213
- Directly calls `execute_plan_actions()` from `tool_caller.py`
- Actually executes tools via the registry
- Returns concrete ToolResult objects

**Method B: `capture_with_crew_tasks()` - BROKEN (CrewAI Orchestration)**
- Location: `crew.py` lines 316-478
- Uses CrewAI's task-based workflow
- Relies on CrewAI agents to execute tools
- Currently being used by ChatCrew (line 311)
- **Problem:** Tool Executor agent doesn't actually call tools!

**ChatCrew is calling the BROKEN method:**
```python
# Line 311 in chat/crew.py
capture_response = await self.capture_crew.capture_with_crew_tasks(
    user_input=user_message,
    context=capture_context,
)
```

#### **Issue #2: Tool Executor Agent Confusion**

The Tool Executor agent's output shows it's **asking for clarification** instead of **executing actions**:

```
Agent: Tool Executor
Final Answer:
I need to clarify what specific tool actions you'd like me to execute.
Looking at your message, I can see:
1. You're referencing a plan that analyzes a Spanish message about David's apartment
2. You mention **memory.note** intent with a memory note creation action
3. You list several clarifications needed about unclear statements
4. But I don't see actual specific tool calls to execute
```

**Why this happens:**
1. The Planner creates a plan with actions
2. The plan is passed to Tool Executor via CrewAI's shared memory
3. Tool Executor receives the plan but **doesn't understand how to extract actions from it**
4. The task description says "Execute the tool actions from the plan" but doesn't provide the actual action list in a format the agent can parse
5. The agent gets confused and asks for clarification

#### **Issue #3: Task Description Mismatch**

The execution_task description (lines 410-425) tells the agent to:
- "Check if the plan has any actions to execute"
- "For each action in the plan..."

But it doesn't actually **provide the actions in a structured format** that the agent can iterate over!

The agent receives the plan as natural language text from the Planner's output, not as a structured object.

#### **Issue #4: No Tool Registry Access in CrewAI Mode**

In `capture_with_crew_tasks()`, the Tool Executor agent has CrewAI tools attached (line 121):
```python
self.tool_caller_agent = create_tool_caller_agent(crewai_llm, tools=crewai_tools)
```

However, the agent doesn't know HOW to call these tools based on the plan output from the Planner.

The direct execution path (`execute_plan_actions()` in tool_caller.py) works because it:
1. Gets the registry directly
2. Iterates over `plan.actions` (structured list)
3. Calls `registry.execute(tool_call)` for each action

The CrewAI path has no such logic - it expects the agent to figure it out from natural language.

---

## ARCHITECTURE COMPARISON

### Working Path (Direct Execution - NOT USED):
```
User Input
  ↓
plan_from_input() → returns Plan object
  ↓
execute_plan_actions(plan) → iterates plan.actions
  ↓
registry.execute(ToolCall) → actual tool execution
  ↓
Returns ToolResult[]
```

### Broken Path (CrewAI - CURRENTLY USED):
```
User Input
  ↓
CrewAI Planning Task → Planner Agent analyzes → returns text description
  ↓
CrewAI Clarification Task → Clarifier Agent → returns text
  ↓
CrewAI Execution Task → Tool Executor Agent → gets confused!
  ↓
Agent asks for clarification instead of executing
  ↓
No tools executed, no ToolResults
```

---

## WHY THIS DESIGN EXISTS

Looking at the code history, it appears:

1. **Original Design**: Direct execution with `capture()` method - works correctly
2. **CrewAI Integration**: Added `capture_with_crew_tasks()` to use CrewAI's agent orchestration and shared memory
3. **Migration Incomplete**: ChatCrew was updated to use the new CrewAI method, but the CrewAI method doesn't actually execute tools properly

The CrewAI approach was likely intended to leverage:
- Shared memory between agents
- More flexible agent-based reasoning
- Better conversation context handling

But the implementation is **incomplete** - it has the agent plumbing but not the actual tool execution logic.

---

## EVIDENCE FROM CONSOLE

**What we see:**
1. ✅ Planner Agent successfully analyzes input
2. ✅ Clarifier Agent determines no clarification needed
3. ❌ Tool Executor Agent gets confused and asks for clarification
4. ❌ No tool execution happens
5. ✅ Conversational Assistant tries to use `<invoke_code>` format (which doesn't work)
6. ✅ Response Composer generates friendly message claiming work was done

**Console shows:**
```
2025-11-02 13:15:35 | ERROR | vitaerules | capture.memory_error
```

This error likely happens when trying to parse results from the CrewAI output, finding no actual tool executions.

---

## POTENTIAL SOLUTIONS

### Option 1: Fix CrewAI Tool Execution (COMPLEX)
**Approach:** Make the Tool Executor agent actually execute tools

**Changes needed:**
1. Modify execution task to provide structured action list
2. Add tool execution logic to the agent's capabilities
3. Ensure agent can call CrewAI-wrapped tools programmatically
4. Parse and return structured ToolResults from agent output

**Pros:**
- Maintains CrewAI architecture
- Keeps shared memory benefits

**Cons:**
- Complex implementation
- Requires deep CrewAI understanding
- May still have agent confusion issues
- Need to handle tool execution errors within agent context

### Option 2: Hybrid Approach - Use Direct Execution (SIMPLE)
**Approach:** Use CrewAI for planning/clarification, direct execution for tools

**Changes needed:**
1. Keep Planner and Clarifier as CrewAI agents
2. Parse the Planner's output into a structured Plan object
3. Use existing `execute_plan_actions()` for tool execution
4. Return properly formatted results

**Pros:**
- Simple and reliable
- Reuses working tool execution code
- Clear separation of concerns
- Agent confusion limited to planning phase

**Cons:**
- Doesn't fully leverage CrewAI orchestration
- Need to parse agent output into structured format

### Option 3: Revert to Direct Execution (SAFEST)
**Approach:** Stop using `capture_with_crew_tasks()`, use original `capture()` method

**Changes needed:**
1. Update ChatCrew line 311 to call `capture()` instead of `capture_with_crew_tasks()`
2. May need to adapt response handling

**Pros:**
- Immediate fix
- Known working implementation
- No agent confusion
- Minimal code changes

**Cons:**
- Loses CrewAI benefits (shared memory, etc.)
- May have other integration issues we haven't tested

---

## RECOMMENDATION

**Implement Option 2: Hybrid Approach**

**Rationale:**
1. Gets tools executing immediately
2. Keeps CrewAI agents for planning (which IS working)
3. Avoids agent confusion in execution phase
4. Clear, maintainable architecture
5. Can still enhance later if needed

**Implementation Steps:**
1. Add a parser to convert Planner agent output → Plan object
2. After Planner task completes, parse the output
3. Skip Tool Executor agent entirely
4. Call `execute_plan_actions()` directly with parsed Plan
5. Return results in expected format

---

## ADDITIONAL OBSERVATIONS

### Conversational Assistant Confusion
In the chat log, we see the Conversational Assistant trying to invoke tools using:
```python
<invoke_code>
{
  "code": "memory_note_tool",
  "args": { ... }
}
</code>
```

This suggests the agent thinks it should format tool calls in XML-like format, but this doesn't trigger actual execution. This is another symptom of the broken tool execution path.

### CaptureCrew Has Two Personalities
The codebase shows CaptureCrew was designed with two execution modes:
1. **Legacy mode**: Direct function calls (working)
2. **CrewAI mode**: Agent-based orchestration (broken)

The ChatCrew only uses CrewAI mode, so users never benefit from the working direct execution.

---

## CONCLUSION

The CaptureCrew tool execution is broken because:
1. It relies on CrewAI agents to execute tools programmatically
2. The Tool Executor agent doesn't understand how to extract and execute actions from the plan
3. No fallback to direct execution exists in the CrewAI code path
4. The working execution code exists but isn't being used

**The fix requires either:**
- Teaching the agent how to execute tools (complex)
- Using direct execution after agent planning (simple)
- Reverting to the working non-CrewAI implementation (safest)

Recommendation: **Hybrid approach** - keep agents for planning, use direct execution for tools.
