# Example Console Output

This shows what the improved logging looks like when using the bot.

## Bot Startup

```
🚀 Starting VitaeRules Telegram Bot...
================================================================================
⚙️  Initializing services...
✓ LLM Service: ollama (qwen3:1.7b)
✓ Tools registered: 4
✓ Memory Service: Connected
================================================================================
✅ Bot is ready! Waiting for messages...
================================================================================
```

## Capturing a Note

**User:** "I had lunch with Alice at the park today"

```
================================================================================
📨 NEW MESSAGE | User: John
================================================================================
💬 Message: I had lunch with Alice at the park today

🧠 PHASE 1: Intent Detection
────────────────────────────────────────────────────────────────────────────────
✓ Intent: note_taking
✓ Confidence: 92%
✓ Action Required: Yes
✓ Entities: {'people': ['Alice'], 'places': ['park']}

💭 PHASE 2: Conversational Response
────────────────────────────────────────────────────────────────────────────────
✓ Response: That sounds lovely! Having lunch at the park with Alice must have been nice. I've saved that memory for you.

⚡ PHASE 3: Action Execution
────────────────────────────────────────────────────────────────────────────────
✓ Target: CAPTURE Crew
  📝 Processing action...
    ├─ Planning...
    ├─ Plan: memory.note (85% confidence)
    ├─ Actions: 1
    └─ Executing actions...
  ✓ Capture complete
  ✓ Actions executed: 1
  ✓ Summary: Saved note about lunch with Alice at the park

================================================================================
✅ MESSAGE PROCESSED SUCCESSFULLY
================================================================================
```

## Asking a Question

**User:** "What did I do with Alice?"

```
================================================================================
📨 NEW MESSAGE | User: John
================================================================================
💬 Message: What did I do with Alice?

🧠 PHASE 1: Intent Detection
────────────────────────────────────────────────────────────────────────────────
✓ Intent: question
✓ Confidence: 95%
✓ Action Required: Yes
✓ Entities: {'people': ['Alice']}

💭 PHASE 2: Conversational Response
────────────────────────────────────────────────────────────────────────────────
✓ Response: Let me check what I remember about your time with Alice!

⚡ PHASE 3: Action Execution
────────────────────────────────────────────────────────────────────────────────
✓ Target: RETRIEVAL Crew
  🔍 Searching memories...
    ├─ Planning query...
    ├─ Query: factual
    ├─ Searching memories...
    ├─ Retrieved: 1 memories
    └─ Composing answer...
  ✓ Found 1 relevant memories
  ✓ Confidence: 85%
  ✓ Answer: You had lunch with Alice at the park today. It sounds like it was a lovely time!...

================================================================================
✅ MESSAGE PROCESSED SUCCESSFULLY
================================================================================
```

## Greeting (No Action)

**User:** "Hello!"

```
================================================================================
📨 NEW MESSAGE | User: John
================================================================================
💬 Message: Hello!

🧠 PHASE 1: Intent Detection
────────────────────────────────────────────────────────────────────────────────
✓ Intent: greeting
✓ Confidence: 98%
✓ Action Required: No

💭 PHASE 2: Conversational Response
────────────────────────────────────────────────────────────────────────────────
✓ Response: Hello! How can I help you today?

================================================================================
✅ MESSAGE PROCESSED SUCCESSFULLY
================================================================================
```

## Error Handling

**User:** Some message that causes an error

```
================================================================================
📨 NEW MESSAGE | User: John
================================================================================
💬 Message: [problematic message]

🧠 PHASE 1: Intent Detection
────────────────────────────────────────────────────────────────────────────────
  ⚠️  Routing fallback due to error: Connection timeout

💭 PHASE 2: Conversational Response
────────────────────────────────────────────────────────────────────────────────
✓ Response: I'm sorry, I didn't quite catch that. Could you rephrase?

❌ ERROR: Connection timeout
================================================================================
```

## Shutdown

```
================================================================================
👋 Shutting down gracefully...
================================================================================
```

---

## Key Benefits

1. **Clear Phases**: Each message processing shows distinct phases (Intent → Response → Action)
2. **Visual Hierarchy**: Box drawing characters (├─ └─) show sub-steps clearly
3. **Success Indicators**: ✓ marks show what succeeded
4. **Compact**: Each message is self-contained but concise
5. **Error Visibility**: Errors are clearly marked with ❌ and red warnings
6. **No Noise**: Suppressed all library debug logs (httpx, telegram, langchain, etc.)
7. **Useful Details**: Shows confidence, intent, entities, action counts - what matters for debugging
