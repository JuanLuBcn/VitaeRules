# Verbose Logging Added to Orchestrator ✅

## Summary of Changes

Added comprehensive logging throughout the orchestrator to track conversation flow, LLM decisions, and tool executions.

## Logging Points Added

### 1. Message Reception (`handle_message`)
```python
self.tracer.info(
    "message_received", 
    extra={
        "chat_id": chat_id,
        "user_id": user_id,
        "message": message[:100],
        "message_length": len(message)
    }
)
```

**Logs:**
- User's message (first 100 chars)
- Message length
- Chat/User IDs

### 2. Media Detection
```python
self.tracer.info(
    "media_detected",
    extra={
        "media_type": media_ref.media_type,
        "has_path": bool(media_ref.media_path)
    }
)
```

### 3. Conversation State
```python
# New conversation
self.tracer.info(
    "new_conversation",
    extra={"chat_id": chat_id, "has_context": False}
)

# Continuing conversation
self.tracer.info(
    "continuing_conversation",
    extra={
        "chat_id": chat_id,
        "waiting_for": context.get("waiting_for"),
        "has_context": True
    }
)
```

### 4. LLM Analysis (`_analyze_message`)
```python
# Before LLM call
self.tracer.info(
    "calling_llm_for_analysis",
    extra={
        "prompt_length": len(prompt),
        "has_media": bool(media_ref)
    }
)

# After LLM response
self.tracer.info(
    "llm_raw_response",
    extra={
        "reply": result.get("reply", "")[:150],
        "tool_call": result.get("tool_call")
    }
)

# Analysis complete
self.tracer.info(
    "llm_analysis_complete",
    extra={
        "reply": reply[:150],
        "has_tool_call": tool_call is not None,
        "tool_name": tool_call.get("name") if tool_call else None,
        "tool_args": list(tool_call.get("args", {}).keys()) if tool_call else None
    }
)
```

**Logs:**
- LLM's response text (first 150 chars)
- Whether LLM wants to call a tool
- Tool name and arguments if tool call

### 5. Tool Execution
```python
# Before execution
self.tracer.info(
    "executing_tool_call",
    extra={
        "tool": tool_call.get("name"),
        "args": tool_call.get("args", {})
    }
)

# After success
self.tracer.info(
    "tool_executed_successfully",
    extra={
        "tool": tool_call.get("name"),
        "result_keys": list(result.keys())
    }
)

# On error
self.tracer.error(
    "tool_execution_error",
    extra={
        "tool": tool_call.get("name"),
        "error": str(e),
        "error_type": type(e).__name__
    }
)
```

### 6. Chat Fallback
```python
# Fallback triggered
self.tracer.info(
    "chat_fallback_triggered",
    extra={
        "tool": tool_call.get("name"),
        "fallback_reason": "empty_results"
    }
)

# Memory search empty
self.tracer.info(
    "memory_search_empty",
    extra={
        "query": query[:100],
        "memories_found": 0,
        "will_fallback": True
    }
)

# Memory search found results
self.tracer.info(
    "memory_search_found",
    extra={
        "query": query[:100],
        "memories_found": len(result.memories),
        "returned": len(results)
    }
)
```

### 7. Conversation Continuation
```python
# Processing user's answer
self.tracer.info(
    "processing_answer",
    extra={
        "answer": answer[:150],
        "previous_question": last_reply[:100],
        "combined_context_length": len(combined_context)
    }
)

# LLM needs more info
self.tracer.info(
    "llm_needs_more_info",
    extra={
        "question": reply[:150],
        "turn_count": len(context)
    }
)

# Conversation complete
self.tracer.info(
    "conversation_complete",
    extra={
        "tool": tool_call.get("name"),
        "turns": len(context)
    }
)
```

### 8. Tool-Specific Logging

**Task Creation:**
```python
self.tracer.info(
    "creating_task",
    extra={
        "user_id": user_id,
        "title": args.get("title", "")[:100],
        "has_due_at": bool(args.get("due_at")),
        "people": args.get("people", [])
    }
)

self.tracer.info(
    "task_created",
    extra={
        "task_id": task_result.get("task_id"),
        "title": args.get("title", "")[:50]
    }
)
```

**Note Saving:**
```python
self.tracer.info(
    "saving_note",
    extra={
        "user_id": user_id,
        "content_length": len(content),
        "content_preview": content[:100],
        "people": args.get("people", []),
        "has_media": bool(args.get("media_path"))
    }
)

self.tracer.info(
    "note_saved",
    extra={
        "title": memory_data["title"],
        "people": memory_data["people"]
    }
)
```

**List Operations:**
```python
self.tracer.info(
    "adding_to_list",
    extra={
        "user_id": user_id,
        "list_name": list_name,
        "items_count": len(items),
        "items": items[:5]
    }
)

self.tracer.info(
    "creating_new_list" / "using_existing_list",
    extra={
        "list_name": list_name,
        "list_id": list_id
    }
)

self.tracer.info(
    "items_added_to_list",
    extra={
        "list_name": list_name,
        "items_added": len(items)
    }
)
```

**Memory Search:**
```python
self.tracer.info(
    "searching_memory",
    extra={
        "query": query[:150],
        "user_id": user_id
    }
)
```

## Example Log Flow

**User: "Recuérdame llamar a Juan mañana"**

```
INFO | message_received | chat_id=123, message="Recuérdame llamar a Juan mañana", message_length=31
INFO | new_conversation | chat_id=123, has_context=False
INFO | analyzing_new_request | message="Recuérdame llamar a Juan mañana", has_media=False
INFO | calling_llm_for_analysis | prompt_length=1247, has_media=False
INFO | llm_raw_response | reply="Claro! ¿Cuándo quieres que te lo recuerde?", tool_call=None
INFO | llm_analysis_complete | reply="Claro! ¿Cuándo quieres...", has_tool_call=False
INFO | llm_asking_question | question="Claro! ¿Cuándo quieres...", needs_more_info=True

[User responds: "Mañana a las 10"]

INFO | message_received | chat_id=123, message="Mañana a las 10", message_length=15
INFO | continuing_conversation | chat_id=123, waiting_for="waiting_for_more", has_context=True
INFO | processing_answer | answer="Mañana a las 10", previous_question="Claro! ¿Cuándo..."
INFO | calling_llm_for_analysis | prompt_length=1350
INFO | llm_raw_response | reply="Perfecto! Te recordaré...", tool_call={"name": "create_task", ...}
INFO | llm_analysis_complete | has_tool_call=True, tool_name="create_task", tool_args=["title", "due_at"]
INFO | answer_triggered_tool | tool="create_task", conversation_turns=3
INFO | executing_tool_call | tool="create_task", args={"title": "llamar a Juan", ...}
INFO | creating_task | title="llamar a Juan", has_due_at=True, people=["Juan"]
INFO | task_created | task_id="abc123", title="llamar a Juan"
INFO | tool_executed_successfully | tool="create_task", result_keys=["success", "task"]
INFO | conversation_complete | tool="create_task", turns=3
```

**User: "¿Qué me dijo María sobre Barcelona?"**

```
INFO | message_received | message="¿Qué me dijo María sobre Barcelona?"
INFO | new_conversation | has_context=False
INFO | analyzing_new_request | message="¿Qué me dijo María sobre Barcelona?"
INFO | calling_llm_for_analysis | prompt_length=1289
INFO | llm_raw_response | reply="Déjame buscar...", tool_call={"name": "search_memory", ...}
INFO | llm_analysis_complete | has_tool_call=True, tool_name="search_memory"
INFO | executing_tool_call | tool="search_memory", args={"query": "María Barcelona"}
INFO | searching_memory | query="María Barcelona", user_id="user123"
INFO | memory_search_empty | query="María Barcelona", memories_found=0, will_fallback=True
INFO | chat_fallback_triggered | tool="search_memory", fallback_reason="empty_results"
INFO | generating_chat_fallback | query="María Barcelona"
INFO | chat_fallback_generated | response="No tengo información guardada sobre eso..."
```

## Benefits

1. **🔍 Complete Visibility**: See every step of conversation processing
2. **🐛 Easy Debugging**: Identify where things go wrong
3. **📊 Flow Tracking**: Understand LLM decision-making
4. **⚡ Performance**: See prompt lengths, tool execution times
5. **🎯 Intent Analysis**: Track what LLM understands vs what user meant

## How to Use

### View Logs in Real-Time
```bash
# Watch trace.jsonl
tail -f data/trace.jsonl | jq .

# Or in PowerShell
Get-Content data/trace.jsonl -Wait -Tail 20
```

### Filter by Event Type
```bash
# See only tool executions
cat data/trace.jsonl | jq 'select(.event | contains("tool"))'

# See LLM decisions
cat data/trace.jsonl | jq 'select(.event | contains("llm"))'

# See memory operations
cat data/trace.jsonl | jq 'select(.event | contains("memory"))'
```

### Common Debugging Scenarios

**"Why didn't the bot create a task?"**
```
Look for:
1. message_received - Did we get the message?
2. llm_analysis_complete - What did LLM understand?
3. has_tool_call - Did LLM decide to call create_task?
4. tool_executed_successfully - Did it execute?
```

**"Why did memory search fail?"**
```
Look for:
1. searching_memory - Was search triggered?
2. memory_search_empty vs memory_search_found - Results?
3. chat_fallback_triggered - Did we fallback?
```

**"Bot keeps asking questions, never executes"**
```
Look for:
1. llm_needs_more_info - How many times?
2. turn_count - Conversation getting stuck?
3. llm_analysis_complete - What args are missing?
```

## Status: ✅ Complete

All major decision points now have comprehensive logging. You can follow the entire conversation flow from user input to tool execution!

---

**Next: Test with real bot to see logs in action!** 🚀
