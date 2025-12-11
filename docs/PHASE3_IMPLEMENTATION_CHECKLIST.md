# Phase 3 Implementation Checklist

**Goal:** Migrate to CrewAI-first architecture with shared memory and agent collaboration

**Status:** 📋 Planning Complete - Ready for Implementation

---

## Quick Reference

### What We're Building

```
Current:                          Target:
┌───────────────────┐            ┌──────────────────┐
│ Orchestrator      │            │ IntentRouter     │
│ (1177 lines)      │            │ (150 lines)      │
│ - Does everything │     →      │ - Just routing   │
└───────────────────┘            └─────────┬────────┘
                                          ↓
                                  ┌───────┴───────┐
                                  ↓               ↓
                              ┌──────────┐  ┌──────────┐
                              │ Crews    │  │ Crews    │
                              │ (Smart)  │  │ (Smart)  │
                              └──────────┘  └──────────┘
                              memory=True   memory=True
```

### Key Features to Implement

1. ✅ Shared memory across agents (CrewAI STM/LTM)
2. ✅ Agent delegation (ChatAgent → SearchAgent)
3. ✅ Unified search (memory + tasks + lists)
4. ✅ Autonomous agents (decide if execute or ask)
5. ✅ Thin orchestrator (just routing)

---

## Phase 3.1: Enable CrewAI Memory (Week 1)

### Tasks

- [ ] **Add Crew objects to RetrievalCrew**
  - File: `src/app/crews/retrieval/crew.py`
  - Change: Create `Crew` object with `memory=True`
  - Lines: ~50 lines
  - Test: Verify agents see each other's outputs

- [ ] **Add Crew objects to CaptureCrew**
  - File: `src/app/crews/capture/crew.py`
  - Change: Create `Crew` object with `memory=True`
  - Lines: ~50 lines
  - Test: Verify memory sharing in capture workflow

- [ ] **Configure CrewAI memory backend**
  - File: `src/app/config.py`
  - Change: Add memory config (provider, collection, embedding)
  - Lines: ~20 lines
  - Test: Verify ChromaDB integration works

- [ ] **Update agent allow_delegation flags**
  - Files: All agent files in `src/app/crews/*/`
  - Change: Set `allow_delegation=True` where needed
  - Lines: ~5 lines per agent
  - Test: No breaking changes

### Testing

```bash
# Run integration tests
pytest tests/integration/test_retrieval_crew.py -v
pytest tests/integration/test_capture_crew.py -v

# Verify memory persistence
pytest tests/integration/test_crew_memory.py -v
```

### Success Criteria

- ✅ Crews use `Crew.kickoff()` instead of manual workflow
- ✅ Agents see context from previous agents
- ✅ Memory persists across crew calls
- ✅ All existing tests pass

---

## Phase 3.2: UnifiedSearchAgent (Week 1-2)

### Tasks

- [ ] **Create search tools**
  - Files: 
    - `src/app/crews/retrieval/tools/memory_search_tool.py`
    - `src/app/crews/retrieval/tools/task_search_tool.py`
    - `src/app/crews/retrieval/tools/list_search_tool.py`
  - Lines: ~50 lines each
  - Test: Each tool searches its source correctly

- [ ] **Create UnifiedSearchAgent**
  - File: `src/app/crews/retrieval/unified_search_agent.py`
  - Lines: ~150 lines
  - Features: Search all sources in parallel, combine results
  - Test: Searches memory + tasks + lists

- [ ] **Add search operations to TaskTool**
  - File: `src/app/tools/task_tool.py`
  - Change: Add `search_tasks` operation
  - Lines: ~30 lines
  - Test: Can search tasks by query

- [ ] **Add search operations to ListTool**
  - File: `src/app/tools/list_tool.py`
  - Change: Add `search_lists` operation
  - Lines: ~30 lines
  - Test: Can search list items by query

- [ ] **Integrate UnifiedSearchAgent into RetrievalCrew**
  - File: `src/app/crews/retrieval/crew.py`
  - Change: Add UnifiedSearchAgent to crew
  - Lines: ~20 lines
  - Test: RetrievalCrew uses unified search

### Testing

```bash
# Test unified search
pytest tests/unit/test_unified_search_agent.py -v

# Test search tools
pytest tests/unit/test_search_tools.py -v

# Integration test
pytest tests/integration/test_unified_search.py -v
```

### Success Criteria

- ✅ Can search memory and find results
- ✅ Can search tasks and find results
- ✅ Can search lists and find results
- ✅ Single query searches all sources
- ✅ Results properly categorized by source

---

## Phase 3.3: ChatCrew (Week 2)

### Tasks

- [ ] **Create ChatCrew structure**
  - Files:
    - `src/app/crews/chat/__init__.py`
    - `src/app/crews/chat/crew.py`
    - `src/app/crews/chat/agents.py`
  - Lines: ~200 lines total
  - Features: Context analysis + conversation agents

- [ ] **Implement ContextAnalyzerAgent**
  - File: `src/app/crews/chat/agents.py`
  - Lines: ~80 lines
  - Features: Decides if need context, delegates to search
  - Test: Correctly identifies when context needed

- [ ] **Implement ConversationAgent**
  - File: `src/app/crews/chat/agents.py`
  - Lines: ~80 lines
  - Features: Generates natural responses with context
  - Test: Responses use search results when available

- [ ] **Wire ChatCrew to orchestrator**
  - File: `src/app/agents/orchestrator.py`
  - Change: Add ChatCrew, route CHAT intent
  - Lines: ~30 lines
  - Test: Chat messages use ChatCrew

### Testing

```bash
# Test ChatCrew
pytest tests/unit/test_chat_crew.py -v

# Test context-aware responses
pytest tests/integration/test_chat_with_context.py -v

# E2E test
pytest tests/e2e/test_chat_flow.py -v
```

### Success Criteria

- ✅ Chat messages search for context automatically
- ✅ Responses include relevant information
- ✅ Chat without context works (general conversation)
- ✅ Multi-turn chat maintains context

---

## Phase 3.4: MemoryCrew (Week 2-3)

### Tasks

- [ ] **Create MemoryCrew structure**
  - Files:
    - `src/app/crews/memory/__init__.py`
    - `src/app/crews/memory/crew.py`
    - `src/app/crews/memory/agents.py`
  - Lines: ~300 lines total

- [ ] **Implement MemoryAnalyzerAgent**
  - File: `src/app/crews/memory/agents.py`
  - Lines: ~100 lines
  - Features: Determine store vs query intent, extract entities
  - Test: Correctly classifies store/query

- [ ] **Implement MemoryEnricherAgent**
  - File: `src/app/crews/memory/agents.py`
  - Lines: ~100 lines
  - Features: Add people, places, temporal context
  - Test: Enrichment adds metadata correctly

- [ ] **Implement MemoryStorerAgent**
  - File: `src/app/crews/memory/agents.py`
  - Lines: ~100 lines
  - Features: Store in LTM or execute query
  - Test: Storage and retrieval work

- [ ] **Create MemoryTool for agent**
  - File: `src/app/tools/memory_tool.py`
  - Lines: ~100 lines
  - Features: Wrap MemoryService for agent use
  - Test: Tool integrates with MemoryService

- [ ] **Wire MemoryCrew to orchestrator**
  - File: `src/app/agents/orchestrator.py`
  - Change: Add MemoryCrew, route MEMORY intents
  - Lines: ~30 lines
  - Test: Memory operations use MemoryCrew

### Testing

```bash
pytest tests/unit/test_memory_crew.py -v
pytest tests/integration/test_memory_storage_flow.py -v
pytest tests/integration/test_memory_query_flow.py -v
```

### Success Criteria

- ✅ Can store notes with enrichment
- ✅ Can query stored information
- ✅ Enrichment adds people, places, time
- ✅ Multi-turn storage (asks for missing info)

---

## Phase 3.5: TaskCrew & ListCrew (Week 3)

### Tasks

- [ ] **Create TaskCrew**
  - Files: `src/app/crews/task/*.py`
  - Lines: ~300 lines
  - Agents: Analyzer, Validator, Executor
  - Test: Task creation with validation

- [ ] **Create ListCrew**
  - Files: `src/app/crews/list/*.py`
  - Lines: ~250 lines
  - Agents: Analyzer, Executor
  - Test: List operations with inference

- [ ] **Wire crews to orchestrator**
  - File: `src/app/agents/orchestrator.py`
  - Change: Route TASK/LIST intents to crews
  - Lines: ~40 lines
  - Test: All operations work

### Testing

```bash
pytest tests/unit/test_task_crew.py -v
pytest tests/unit/test_list_crew.py -v
pytest tests/integration/test_task_flow.py -v
pytest tests/integration/test_list_flow.py -v
```

### Success Criteria

- ✅ Tasks created with smart defaults
- ✅ Lists infer name from context
- ✅ Validation works (asks for missing required fields)
- ✅ Direct operations (list tasks) work instantly

---

## Phase 3.6: IntentOrchestrator (Week 4)

### Tasks

- [ ] **Create IntentOrchestrator**
  - File: `src/app/agents/intent_orchestrator.py`
  - Lines: ~300 lines
  - Features: Semantic intent detection, routing, context management
  - Test: Routes correctly to all crews

- [ ] **Create IntentDetectorAgent**
  - Part of IntentOrchestrator
  - Lines: ~50 lines (agent definition)
  - Features: Fast semantic intent classification
  - Test: 80%+ accuracy on test cases

- [ ] **Implement context management**
  - Part of IntentOrchestrator
  - Lines: ~100 lines
  - Features: Track conversation state, pass context to crews
  - Test: Multi-turn conversations work

- [ ] **Update TelegramAdapter**
  - File: `src/adapters/telegram_bot.py`
  - Change: Use IntentOrchestrator instead of ConversationalOrchestrator
  - Lines: ~10 lines
  - Test: All Telegram flows work

- [ ] **Keep ConversationalOrchestrator for rollback**
  - Rename: `orchestrator.py` → `orchestrator_old.py`
  - Reason: Easy rollback if issues
  - Test: Can switch back if needed

### Testing

```bash
# Test intent detection
pytest tests/unit/test_intent_detection.py -v

# Test routing
pytest tests/unit/test_intent_orchestrator.py -v

# E2E tests
pytest tests/e2e/test_all_flows.py -v

# Regression tests
pytest tests/integration/ -v
```

### Success Criteria

- ✅ All existing flows work
- ✅ Intent detection accurate (80%+)
- ✅ Context passed to crews
- ✅ Multi-turn works
- ✅ Performance acceptable (<2s p95)
- ✅ Zero regressions

---

## Phase 3.7: Agent Delegation (Week 5)

### Tasks

- [ ] **Enable delegation on ContextAnalyzerAgent**
  - File: `src/app/crews/chat/agents.py`
  - Change: `allow_delegation=True`
  - Lines: 1 line
  - Test: Can delegate to SearchAgent

- [ ] **Test delegation flow**
  - Test: ChatAgent → ContextAnalyzer → UnifiedSearchAgent → Response
  - Test: Delegation happens automatically
  - Test: Results returned correctly

- [ ] **Optimize delegation performance**
  - Monitor: Latency of delegated calls
  - Optimize: If needed, cache common queries
  - Test: Performance acceptable

### Testing

```bash
pytest tests/integration/test_agent_delegation.py -v
pytest tests/performance/test_delegation_latency.py -v
```

### Success Criteria

- ✅ ChatAgent delegates to SearchAgent
- ✅ Search results returned to ChatAgent
- ✅ Response includes search context
- ✅ Performance acceptable

---

## Final Testing & Validation (Week 5-6)

### Full Test Suite

- [ ] **Unit tests**
  ```bash
  pytest tests/unit/ -v --cov=src/app/crews --cov=src/app/agents
  ```
  - Target: >80% coverage

- [ ] **Integration tests**
  ```bash
  pytest tests/integration/ -v
  ```
  - Target: All flows work

- [ ] **E2E tests**
  ```bash
  pytest tests/e2e/ -v
  ```
  - Target: Real conversation flows work

- [ ] **Performance tests**
  ```bash
  pytest tests/performance/ -v
  ```
  - Target: <2s p95 response time

### Regression Testing

- [ ] Test all existing functionality
- [ ] Compare with ConversationalOrchestrator behavior
- [ ] Document any differences
- [ ] Fix any regressions

### User Acceptance Testing

- [ ] Real Telegram conversations
- [ ] Test all intents (memory, tasks, lists, chat, query)
- [ ] Test multi-turn conversations
- [ ] Test edge cases
- [ ] Get feedback from users

---

## Rollback Plan

If issues arise:

1. **Immediate Rollback**
   ```python
   # src/adapters/telegram_bot.py
   from app.agents.orchestrator_old import ConversationalOrchestrator
   self.orchestrator = ConversationalOrchestrator(llm, memory)
   ```

2. **Feature Flag Rollback**
   ```python
   # src/config.py
   USE_CREWAI_ORCHESTRATION = os.getenv("USE_CREWAI", "false") == "true"
   
   # src/adapters/telegram_bot.py
   if USE_CREWAI_ORCHESTRATION:
       self.orchestrator = IntentOrchestrator(llm, memory)
   else:
       self.orchestrator = ConversationalOrchestrator(llm, memory)
   ```

3. **Gradual Rollout**
   - Start with 10% of users
   - Monitor metrics (errors, latency, user feedback)
   - Increase to 50%, then 100%
   - Rollback if issues detected

---

## Monitoring & Metrics

### Key Metrics to Track

1. **Performance**
   - Response time (p50, p95, p99)
   - LLM call count per message
   - Memory usage
   - Error rate

2. **Accuracy**
   - Intent detection accuracy
   - Search result relevance
   - User satisfaction (thumbs up/down)

3. **Usage**
   - Messages per crew
   - Delegation frequency
   - Multi-turn conversation rate

### Monitoring Tools

```python
# src/app/tracing/metrics.py

class CrewMetrics:
    @staticmethod
    def track_crew_execution(crew_name, duration_ms, success):
        """Track crew execution metrics."""
        
    @staticmethod
    def track_intent_detection(intent, confidence, correct):
        """Track intent detection accuracy."""
        
    @staticmethod
    def track_delegation(from_agent, to_agent, duration_ms):
        """Track agent delegation."""
```

---

## Documentation Updates

- [ ] Update README with new architecture
- [ ] Update API documentation
- [ ] Create crew usage guide
- [ ] Document intent detection strategy
- [ ] Add examples for each crew
- [ ] Update deployment guide

---

## Summary

**Total Effort:** ~30 days (6 weeks)

**Phases:**
1. ✅ Enable CrewAI memory (3 days)
2. ✅ UnifiedSearchAgent (4 days)
3. ✅ ChatCrew (3 days)
4. ✅ MemoryCrew (5 days)
5. ✅ TaskCrew & ListCrew (5 days)
6. ✅ IntentOrchestrator (4 days)
7. ✅ Agent delegation (2 days)
8. ✅ Testing & validation (4 days)

**Deliverables:**
- ✅ 5 specialized crews (Memory, Task, List, Retrieval, Chat)
- ✅ Unified search across all sources
- ✅ Thin orchestrator (just routing)
- ✅ Shared memory (CrewAI STM/LTM)
- ✅ Agent delegation (ChatAgent → SearchAgent)
- ✅ Full test coverage (>80%)
- ✅ Documentation

**Ready to start! 🚀**

---

## Quick Start

To begin implementation:

```bash
# 1. Create feature branch
git checkout -b feature/phase3-crewai-orchestration

# 2. Start with Phase 3.1 (Enable memory)
# Edit: src/app/crews/retrieval/crew.py
# Add: Crew object with memory=True

# 3. Run tests
pytest tests/integration/test_retrieval_crew.py -v

# 4. Commit and move to next phase
git commit -m "Phase 3.1: Enable CrewAI memory on RetrievalCrew"

# 5. Continue through phases 3.2 → 3.7
```

Good luck! 🎯
