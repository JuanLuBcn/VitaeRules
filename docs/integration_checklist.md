# Integration Checklist

## ✅ Pre-Integration (Completed)

- [x] Create BaseAgent interface
- [x] Create IntentClassifier
- [x] Create ListAgent
- [x] Create TaskAgent
- [x] Create NoteAgent
- [x] Create QueryAgent
- [x] Create AgentOrchestrator
- [x] Create test suite
- [x] Create migration guide
- [x] Create quick reference
- [x] Create visual diagrams
- [x] All files compile without errors

## 📋 Integration Tasks

### Phase 1: Testing (Estimated: 30 minutes)

- [ ] **Test Intent Classification**
  ```bash
  python scripts/test_agent_architecture.py
  ```
  - [ ] Verify all 7 test cases pass
  - [ ] Check confidence scores are reasonable
  - [ ] Test edge cases (empty, unclear messages)

- [ ] **Test Individual Agents**
  - [ ] ListAgent: Add, query, multiple items
  - [ ] TaskAgent: Create, query
  - [ ] NoteAgent: Save with metadata
  - [ ] QueryAgent: Search and retrieve
  
- [ ] **Test Orchestrator**
  - [ ] Message routing
  - [ ] Confirmation flow
  - [ ] Low confidence handling
  - [ ] Unknown intent handling

### Phase 2: Telegram Integration (Estimated: 40 minutes)

- [ ] **Update telegram.py imports**
  ```python
  from app.agents.orchestrator import AgentOrchestrator
  ```

- [ ] **Initialize orchestrator in __init__**
  ```python
  self.orchestrator = AgentOrchestrator(self.llm, self.memory)
  ```

- [ ] **Replace message handling**
  - [ ] Find existing `handle_message()` method
  - [ ] Replace Router call with orchestrator
  - [ ] Replace Planner call with orchestrator
  - [ ] Update confirmation handling
  - [ ] Remove old heuristic calls

- [ ] **Test locally**
  - [ ] Send test messages via Telegram
  - [ ] Verify intents classified correctly
  - [ ] Test confirmation flow
  - [ ] Test all agent types

### Phase 3: Deployment (Estimated: 30 minutes)

- [ ] **Add feature flag**
  ```python
  USE_NEW_AGENT_SYSTEM = os.getenv("USE_NEW_AGENTS", "false") == "true"
  
  if USE_NEW_AGENT_SYSTEM:
      result = await self.orchestrator.handle_message(...)
  else:
      # Old system
      ...
  ```

- [ ] **Deploy to staging**
  - [ ] Set `USE_NEW_AGENTS=false` (use old system)
  - [ ] Deploy code
  - [ ] Verify old system still works
  - [ ] Set `USE_NEW_AGENTS=true` (use new system)
  - [ ] Test new system in staging

- [ ] **Monitor metrics**
  - [ ] Response time
  - [ ] Error rate
  - [ ] Intent classification accuracy
  - [ ] User satisfaction

### Phase 4: Production Rollout (Estimated: 1 week)

- [ ] **Week 1: 10% traffic**
  - [ ] Deploy with 10% feature flag
  - [ ] Monitor closely for errors
  - [ ] Compare old vs new metrics
  - [ ] Fix any issues

- [ ] **Week 2: 50% traffic**
  - [ ] Increase to 50% if no issues
  - [ ] Continue monitoring
  - [ ] Collect user feedback

- [ ] **Week 3: 100% traffic**
  - [ ] Switch fully to new system
  - [ ] Monitor for 1 week
  - [ ] Verify stability

- [ ] **Week 4: Cleanup**
  - [ ] If stable, remove old code
  - [ ] Update documentation
  - [ ] Mark migration complete

### Phase 5: Cleanup (Estimated: 1 hour)

- [ ] **Remove old code**
  - [ ] Delete `src/app/llm/router.py`
  - [ ] Delete `src/app/crews/capture/planner.py`
  - [ ] Remove heuristic functions:
    - [ ] `is_question()`
    - [ ] `is_list_query()`
    - [ ] `extract_list_name()`
  - [ ] Remove old intent enums
  - [ ] Clean up unused imports

- [ ] **Update main documentation**
  - [ ] Update README with new architecture
  - [ ] Remove references to old system
  - [ ] Add links to new docs

- [ ] **Archive old code**
  - [ ] Create `archive/old_system/` directory
  - [ ] Move old files there for reference
  - [ ] Add note about when archived

## 🧪 Test Scenarios

### Must Test Before Deploying

- [ ] **Lists**
  - [ ] "Añade mantequilla a la lista de la compra" → Add single item
  - [ ] "Berenjenas, tomates y aguacates" → Add multiple items
  - [ ] "Qué hay en la lista?" → Query list
  - [ ] Case-insensitive list names

- [ ] **Tasks**
  - [ ] "Remind me to call John tomorrow" → Create task
  - [ ] "I need to finish report by Friday" → Create with date
  - [ ] "What are my tasks?" → Query tasks
  - [ ] Natural date parsing

- [ ] **Notes**
  - [ ] "Remember that John likes coffee" → Save note
  - [ ] "Barcelona is beautiful" → Extract place
  - [ ] "Note: Meeting with Sarah went well" → Extract person
  - [ ] Metadata extraction

- [ ] **Queries**
  - [ ] "What did I do yesterday?" → Search by date
  - [ ] "Tell me about John" → Search by person
  - [ ] "When is the deadline?" → Search by keyword
  - [ ] Source citations

- [ ] **Edge Cases**
  - [ ] Unclear message → Clarification
  - [ ] Very long message → Handle gracefully
  - [ ] Empty message → Error handling
  - [ ] Special characters → No crashes
  - [ ] Multiple intents → Pick strongest

- [ ] **Confirmation Flow**
  - [ ] "yes" → Execute
  - [ ] "no" → Cancel
  - [ ] "sí" → Execute (Spanish)
  - [ ] Timeout → Clear pending
  - [ ] Multiple pending → Per-chat isolation

## 📊 Metrics to Monitor

### Before Deployment (Baseline)
- [ ] Record current response times
- [ ] Record current error rate
- [ ] Record current user satisfaction
- [ ] Save conversation logs for comparison

### After Deployment (Compare)
- [ ] Response time: Faster? Same? Slower?
- [ ] Error rate: Lower? Same? Higher?
- [ ] User satisfaction: Better? Same? Worse?
- [ ] Intent accuracy: Measure confidence scores

### Success Criteria
- [ ] Response time: <= current baseline
- [ ] Error rate: <= current baseline
- [ ] User satisfaction: >= current baseline
- [ ] Intent accuracy: >= 90% confidence on clear messages

## 🐛 Known Issues to Watch

- [ ] **ListAgent.remove()**: Not implemented (returns "not implemented")
- [ ] **TaskAgent.complete()**: Not implemented (returns "not implemented")
- [ ] **Confirmation state**: In-memory only (lost on restart)
- [ ] **Confidence threshold**: 0.7 may need tuning
- [ ] **Date parsing**: Relies on LLM, may vary

## 🔧 Quick Fixes if Issues Arise

### If intent classification is wrong:
1. Check confidence scores in logs
2. Adjust threshold (currently 0.7)
3. Add more examples to IntentClassifier prompt
4. Tune LLM parameters

### If confirmations not working:
1. Check pending_confirmations state
2. Verify chat_id matching
3. Check yes/no detection logic
4. Add more confirmation keywords

### If agents failing:
1. Check agent-specific logs
2. Verify tool availability (ListTool, TaskTool, etc.)
3. Test extraction logic separately
4. Verify database connections

### If too slow:
1. Profile LLM calls
2. Consider caching classifier results
3. Optimize extraction prompts
4. Batch operations if possible

## 📝 Code Changes Needed

### telegram.py - Main Changes

**Before:**
```python
# Old system
intent = await self.router.classify(message)
planner_intent = await self.planner.detect_intent(message)

if is_question(message):
    result = await self.retrieval_crew.process(...)
elif is_list_query(message):
    result = await self.list_tool.query(...)
else:
    result = await self.capture_crew.process(...)
```

**After:**
```python
# New system
result = await self.orchestrator.handle_message(
    message=message,
    chat_id=chat_id,
    user_id=user_id,
)

if result["needs_confirmation"]:
    await self.send_message(result["message"])
    # Confirmation handled by orchestrator
else:
    await self.send_message(result["message"])
```

### Confirmation Handling

**Before:**
```python
# Manual confirmation tracking
if message in ["yes", "sí"]:
    # Execute pending action
    ...
```

**After:**
```python
# Orchestrator handles it
result = await self.orchestrator.handle_message(
    message=message,  # "yes" or "no"
    chat_id=chat_id,
    user_id=user_id,
)
```

## 🎯 Success Indicators

You'll know the migration is successful when:

- [x] All tests pass
- [ ] No errors in production logs
- [ ] Response times same or better
- [ ] Users don't notice the change
- [ ] Intent classification >= 90% accurate
- [ ] Confirmations work smoothly
- [ ] All agent types working (list, task, note, query)
- [ ] Can easily add new agents

## 🚨 Rollback Triggers

Rollback to old system if:

- [ ] Error rate increases by >10%
- [ ] Response time increases by >50%
- [ ] Critical functionality broken
- [ ] User complaints increase significantly
- [ ] Data loss or corruption

## 📅 Timeline Summary

| Phase | Duration | Tasks |
|-------|----------|-------|
| Testing | 30 min | Run test suite, verify all scenarios |
| Integration | 40 min | Update telegram.py, test locally |
| Deployment | 30 min | Deploy to staging, add feature flag |
| Monitoring | 1 week | 10% → 50% → 100% traffic |
| Cleanup | 1 hour | Remove old code, update docs |
| **Total** | **~1.5 weeks** | Including monitoring period |

## ✅ Final Checklist

Before marking as complete:

- [ ] All tests passing
- [ ] No errors in production
- [ ] All 4 agent types working
- [ ] Confirmation flow working
- [ ] Metrics stable or improved
- [ ] Old code removed
- [ ] Documentation updated
- [ ] Team trained on new system

## 🎉 Completion

When all boxes checked:

- [ ] Mark migration as complete
- [ ] Celebrate! 🎊
- [ ] Share learnings with team
- [ ] Plan next agent to add (events? reminders?)

---

**Current Status**: ✅ Pre-integration complete, ready for testing

**Next Step**: Run `python scripts/test_agent_architecture.py`

**Questions?** Check:
- `docs/migration_guide.md` - Full migration instructions
- `docs/agent_quick_reference.md` - Code examples
- `docs/agent_architecture_diagrams.md` - Visual guides
