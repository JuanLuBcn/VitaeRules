# Semantic Search Investigation

## Problem Report

User reported: "Retrieval seems to found all available memories instead of using semantic search."

## Investigation Results

### Test Setup
Created 3 diverse memories:
1. **Pizza Lunch** - Food/restaurant content
2. **Python Code Review** - Programming/technical content  
3. **Car Maintenance** - Vehicle/mechanical content

### Test Results

#### Test 1: Query "programming and code reviews"
```
1. Python Code Review  - Score: 0.4894 ✅ Correct match
2. Car Maintenance     - Score: 0.3791 ❌ Irrelevant
3. Pizza Lunch         - Score: 0.3479 ❌ Irrelevant
```

#### Test 2: Query "food and restaurants"
```
1. Pizza Lunch         - Score: 0.4418 ✅ Correct match
2. Car Maintenance     - Score: 0.3586 ❌ Irrelevant
3. Python Code Review  - Score: 0.3258 ❌ Irrelevant
```

#### Test 3: Query "vehicle maintenance"
```
1. Car Maintenance     - Score: 0.4279 ✅ Correct match
2. Pizza Lunch         - Score: 0.3386 ❌ Irrelevant
3. Python Code Review  - Score: 0.3323 ❌ Irrelevant
```

## Root Cause

**Semantic search IS working correctly** - it's using Chroma's vector similarity and ranking by relevance.

**The issue**: No minimum relevance score threshold.

Current behavior in `long_term.py`:
```python
def search(self, query: MemoryQuery) -> list[MemorySearchResult]:
    results = self.collection.query(
        query_texts=[query.query],
        n_results=query.top_k,  # Returns up to top_k results
        where=where_filter if where_filter else None,
        include=["documents", "metadatas", "distances"],
    )
    
    # Converts ALL results, no score filtering
    for i, item_id in enumerate(results["ids"][0]):
        score = 1.0 / (1.0 + distance)
        search_results.append(...)  # Appends regardless of score
```

## Current System Behavior

**What happens**:
- System requests `top_k=10` results
- With only 3 memories, it returns all 3
- No filtering by minimum score
- User sees ALL memories regardless of relevance

**Why this appears broken**:
- Query "What is the weather?" returns conversation about pizza
- Query "programming" returns memories about cars
- Gives impression semantic search isn't working

## The Fix

Add a minimum relevance score threshold to filter out low-scoring results.

### Recommended Approach

**Option 1: Hard threshold** (Simple, immediate)
```python
MIN_RELEVANCE_SCORE = 0.40  # Only return results >= 40% relevant

for i, item_id in enumerate(results["ids"][0]):
    score = 1.0 / (1.0 + distance)
    
    if score >= MIN_RELEVANCE_SCORE:  # ✅ Add threshold check
        search_results.append(...)
```

**Option 2: Configurable threshold** (Better, flexible)
```python
# In MemoryQuery schema
class MemoryQuery(BaseModel):
    query: str
    top_k: int = 10
    min_score: float = 0.40  # ✅ Add configurable threshold
    ...

# In LongTermMemory.search()
for i, item_id in enumerate(results["ids"][0]):
    score = 1.0 / (1.0 + distance)
    
    if score >= query.min_score:  # ✅ Use configured threshold
        search_results.append(...)
```

**Option 3: Dynamic threshold** (Most sophisticated)
```python
# Calculate median or mean score of results
# Only keep results significantly above average
# Adapts to result quality automatically
```

### Recommended Threshold Values

Based on test results:
- **Strong relevance**: 0.45+ (top match)
- **Moderate relevance**: 0.40-0.45 (might be useful)
- **Weak relevance**: 0.35-0.40 (probably not useful)
- **Irrelevant**: < 0.35 (should be filtered)

**Recommended starting threshold**: `0.40`

This would give:
- Programming query → Only Python (0.4894) ✅
- Food query → Only Pizza (0.4418) ✅  
- Vehicle query → Only Car (0.4279) ✅

## Implementation Plan

### Step 1: Add threshold to MemoryQuery
**File**: `src/app/memory/schemas.py`

```python
class MemoryQuery(BaseModel):
    """Query for searching memories."""
    
    query: str
    top_k: int = 10
    min_score: float = 0.40  # ✅ Add this field
    
    # ... rest of fields
```

### Step 2: Apply threshold in search
**File**: `src/app/memory/long_term.py`

```python
def search(self, query: MemoryQuery) -> list[MemorySearchResult]:
    # ... existing query code ...
    
    search_results = []
    if results["ids"] and results["ids"][0]:
        for i, item_id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i]
            distance = results["distances"][0][i] if results["distances"] else 1.0
            score = 1.0 / (1.0 + distance)
            
            # ✅ Add threshold check
            if score >= query.min_score:
                item = self._reconstruct_item(metadata)
                search_results.append(
                    MemorySearchResult(
                        item=item,
                        score=score,
                        highlights=[],
                    )
                )
    
    return search_results
```

### Step 3: Update retriever to use threshold
**File**: `src/app/crews/retrieval/retriever.py`

```python
memory_query = MemoryQuery(
    query=query.query_text,
    top_k=query.max_results,
    min_score=0.40,  # ✅ Set threshold
    people=query.filters.people if query.filters else None,
    # ... rest of fields
)
```

### Step 4: Test the fix
Run `scripts/test_semantic_search.py` again and verify:
- Programming query returns only Python (not all 3)
- Food query returns only Pizza (not all 3)
- Vehicle query returns only Car (not all 3)

### Step 5: Add configuration
**File**: `src/app/config.py`

```python
class Settings(BaseSettings):
    # ... existing fields ...
    
    # Memory settings
    memory_relevance_threshold: float = 0.40  # ✅ Add this
```

Update retriever to use config:
```python
memory_query = MemoryQuery(
    query=query.query_text,
    top_k=query.max_results,
    min_score=settings.memory_relevance_threshold,  # ✅ Use config
    # ... rest
)
```

## Expected Impact

### Before (Current)
```
User: "Tell me about programming"
System returns:
  1. Python Code Review (relevant)
  2. Car Maintenance (irrelevant)
  3. Pizza Lunch (irrelevant)
User: "Why is it showing me car and pizza??"
```

### After (With Threshold)
```
User: "Tell me about programming"
System returns:
  1. Python Code Review (0.4894 > 0.40 ✅)
  (Car: 0.3791 < 0.40 ❌ filtered out)
  (Pizza: 0.3479 < 0.40 ❌ filtered out)
User: "Perfect! Just what I wanted."
```

## Edge Cases to Consider

1. **No results above threshold**
   - Query: "nuclear physics" (no related memories)
   - Result: Empty list (correct behavior)
   - System should respond: "I don't have information about that"

2. **Very specific query**
   - Query: "Python async/await patterns"
   - If no exact match, might get score 0.35-0.40
   - Could miss relevant memory if threshold too high
   - Solution: User can ask "tell me about programming" (broader)

3. **Multiple high-scoring results**
   - Query: "What did I do today?"
   - Multiple memories might score > 0.40
   - This is correct behavior (return all relevant)

## Testing Checklist

- [ ] Add `min_score` field to `MemoryQuery`
- [ ] Update `search()` to filter by threshold
- [ ] Update retriever to use threshold
- [ ] Run semantic search test - verify only relevant results
- [ ] Test edge case: query with no relevant memories
- [ ] Test edge case: query with multiple relevant memories
- [ ] Update integration tests
- [ ] Add threshold to config (optional but recommended)
- [ ] Document behavior in user-facing docs

## Conclusion

**Semantic search is working correctly** - it's ranking by relevance using vector similarity.

**The fix is simple**: Add a minimum score threshold of ~0.40 to filter out low-scoring results.

**Why this matters**: Without threshold filtering, users see ALL memories including irrelevant ones, making it appear that semantic search isn't working at all. With threshold filtering, users only see truly relevant memories.

**Recommendation**: Implement Option 2 (configurable threshold) with default value 0.40.
