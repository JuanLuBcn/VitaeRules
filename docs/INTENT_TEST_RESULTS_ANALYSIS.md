# Intent Detection Test Results - Analysis

## Run Date: October 28, 2025

## Overall Results
- **Accuracy**: 70.4% (19/27 correct)
- **Target**: ≥85%
- **Status**: ⚠️ NEEDS IMPROVEMENT

## Performance by Category

### ✅ Excellent (100%)
- **CHAT**: 6/6 (100%) - Perfect detection of general conversation
- **TASK_CREATE**: 3/3 (100%) - Perfect detection of reminders
- **COMPOSITE**: 2/2 (100%) - Perfect detection of multi-intent

### ⚠️ Needs Work
- **QUERY**: 4/5 (80%) - Good but one false negative
- **STORE**: 2/4 (50%) - **MAIN PROBLEM**
- **LIST_ADD**: 1/3 (33%) - Confused with TASK_CREATE
- **AMBIGUOUS**: 1/4 (25%) - Too confident in MEMORY_QUERY

## Key Problems Identified

### Problem 1: "X me dijo Y" Misclassified

**Issue**: LLM thinks "me dijo" means asking for memory
```
Input: "María me dijo que se muda a Barcelona"
Expected: MEMORY_STORE (user is INFORMING us)
Detected: MEMORY_QUERY (LLM thinks asking for what María said)
```

**Root Cause**: 
- "me dijo" triggers past tense association
- LLM doesn't distinguish between:
  - "¿Qué me dijo María?" (QUERY - asking)
  - "María me dijo que..." (STORE - telling)

**Solution**:
Add clarification: "X me dijo Y" is AFFIRMING new info, not ASKING

---

### Problem 2: Ambiguous Questions → MEMORY_QUERY (Too Confident)

**Issue**: Should default to CHAT for ambiguous cases
```
Input: "¿Qué sabes de Barcelona?"
Expected: CHAT (ambiguous, fallback)
Detected: MEMORY_QUERY (0.90 confidence!)
```

**Root Cause**:
- "qué sabes" sounds like asking for stored knowledge
- LLM assumes everything is in memory
- Fallback rule not strong enough

**Solution**:
Strengthen: "If no explicit past reference → CHAT"

---

### Problem 3: "Comprar X" = LIST_ADD or TASK_CREATE?

**Issue**: Semantic overlap
```
Input: "Comprar pan y huevos"
Expected: LIST_ADD (add to shopping list)
Detected: TASK_CREATE (reminder to buy)
```

**Analysis**:
- Both make sense semantically!
- "Comprar X" IS a future action (task)
- But also IS adding to shopping list

**Questions**:
1. Should we have LIST_ADD at all?
2. Or should "comprar X" → TASK_CREATE with tag:shopping?
3. Does LIST_ADD only apply when "lista" is mentioned?

---

### Problem 4: Single Word "Leche" → CHAT (0.00 confidence)

**Issue**: Ultra-ambiguous input
```
Input: "Leche"
Expected: LIST_ADD
Detected: CHAT (0.00 confidence - totally uncertain)
```

**Analysis**:
- LLM is right to be uncertain
- Single word could mean anything
- This should trigger clarification question

**Solution**:
- Accept that ultra-short messages need clarification
- Maybe: If confidence < 0.5 → Ask user to clarify

---

## Recommendations

### 1. Immediate Prompt Fixes

#### Fix A: Clarify STORE vs QUERY for "X dijo Y"
```
MEMORY_STORE: User is AFFIRMING/TELLING you something
  - "María me dijo que..." (user is INFORMING you)
  - "Resulta que X es Y" (user is TELLING you a fact)
  
MEMORY_QUERY: User is ASKING you for stored info
  - "¿Qué me dijo María?" (user is ASKING)
  - "¿Cuándo fue...?" (user is ASKING)
```

#### Fix B: Strengthen CHAT Fallback
```
CRITICAL RULE:
- Questions WITHOUT explicit past references → Default to CHAT
- "¿Qué sabes de X?" → CHAT (ambiguous)
- "¿Qué me dijiste de X?" → MEMORY_QUERY (explicit past)
- "¿Por qué X?" → CHAT (reasoning, may use context)

When uncertain → ALWAYS choose CHAT
```

#### Fix C: LIST_ADD Clarification
```
Decision needed:
  
Option A: LIST_ADD only when "lista" mentioned
  "Añade leche a la lista" → LIST_ADD
  "Comprar leche" → TASK_CREATE
  
Option B: LIST_ADD for shopping items
  "Comprar leche" → LIST_ADD (infer shopping list)
  "Leche" → LIST_ADD (infer shopping list)
  
Recommendation: Option A (explicit is better)
```

### 2. Expected Accuracy After Fixes
- **STORE**: 50% → **90%** (fix "me dijo" issue)
- **QUERY**: 80% → **85%** (strengthen)
- **AMBIGUOUS**: 25% → **75%** (strengthen fallback)
- **LIST_ADD**: Need to decide on strategy

**Projected Overall**: **~80-85%** ✅

### 3. Acceptance Criteria

After prompt refinement:
- Clear cases: ≥95%
- Ambiguous cases: ≥70% (acceptable for fallback)
- Overall: ≥85%

### 4. Long-term Improvements

If accuracy remains < 85% after prompt fixes:
1. **Better model**: Upgrade from qwen3:1.7b → qwen3:8b or llama3:8b
2. **Few-shot examples**: Add 2-3 examples per category (compromises pure semantic)
3. **Hybrid approach**: Keywords + LLM for edge cases
4. **Fine-tuning**: Train on real user messages

## Test Cases to Add

### More STORE variations
```
"Juan vive en Barcelona"
"El meeting es a las 3pm"
"La contraseña del wifi es 12345"
```

### More QUERY variations
```
"¿Dónde vive Juan?"
"¿A qué hora es el meeting?"
"¿Cuál es la contraseña del wifi?"
```

### More ambiguous cases
```
"¿Qué hay de nuevo?"
"¿Cómo va el proyecto?"
"¿Todo bien con María?"
```

## Next Steps

1. ✅ Refine prompt based on Fix A, B, C
2. ⏳ Re-run test (target: ≥80%)
3. ⏳ If ≥80% → Implement in Agent Zero
4. ⏳ If <80% → Consider model upgrade

## Questions for Discussion

### Q1: LIST_ADD Strategy
Should "Comprar X" be:
- **A)** LIST_ADD (always assume shopping list)
- **B)** TASK_CREATE (it's a future action)
- **C)** LIST_ADD only if "lista" mentioned explicitly

**Recommendation**: C (explicit is safer)

### Q2: Confidence Threshold
What to do when confidence < 0.5?
- **A)** Default to CHAT (current strategy)
- **B)** Ask user to clarify
- **C)** Show uncertainty: "No estoy seguro, ¿quieres...?"

**Recommendation**: A for now, B for future improvement

### Q3: "me dijo" Handling
Is "X me dijo Y" always STORE?
- **A)** Yes, it's always affirming new info
- **B)** No, check question mark: "¿X me dijo Y?" → QUERY

**Recommendation**: B (check if it's a question)

---

## Conclusion

**Status**: Promising but needs prompt refinement

**The good**:
- ✅ Model understands core semantics
- ✅ Perfect on clear CHAT and TASK cases
- ✅ No catastrophic failures

**The issues**:
- ⚠️ "me dijo" pattern confusion (fixable)
- ⚠️ Ambiguous → MEMORY_QUERY bias (fixable)
- ⚠️ LIST_ADD strategy unclear (design decision)

**Confidence**: With prompt fixes, we can reach **80-85%** accuracy ✅

**Ready to implement?** After one more iteration with refined prompt
