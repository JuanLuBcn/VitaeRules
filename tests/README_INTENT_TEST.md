# Intent Detection Performance Test

## Purpose

Test the LLM's ability to classify user messages into intents **semantically** (without keyword matching) before implementing the full Agent Zero architecture.

## What It Tests

### Intent Categories

1. **MEMORY_STORE** - User wants to save information
2. **MEMORY_QUERY** - User wants to retrieve stored information
3. **TASK_CREATE** - User wants to create a reminder/task
4. **LIST_ADD** - User wants to add items to a list
5. **CHAT** - General conversation, opinions, advice
6. **COMPOSITE** - Multiple intents in one message

### Test Cases (30+ examples)

- **Clear cases**: High-confidence expected (>0.85)
- **Ambiguous cases**: Lower confidence expected (0.50-0.70)
- **Edge cases**: Composite intents, single words

## Running the Test

```bash
# Activate environment
.venv\Scripts\Activate.ps1

# Set PYTHONPATH and run
$env:PYTHONPATH="src"; python tests/test_intent_detection.py
```

## Expected Output

```
================================================================================
INTENT DETECTION PERFORMANCE TEST
================================================================================

[Test 1/30] Category: store_clear
Message: "María me dijo que se muda a Barcelona en marzo"
Expected: MEMORY_STORE (confidence ≥ 0.85)
Detected: MEMORY_STORE (confidence: 0.95) ✅ PASS
Reasoning: User is stating information to store about María

[Test 2/30] Category: query_clear
Message: "¿Qué me dijo María?"
Expected: MEMORY_QUERY (confidence ≥ 0.90)
Detected: MEMORY_QUERY (confidence: 0.98) ✅ PASS
Reasoning: User is asking for past conversation (personal query)

...

================================================================================
SUMMARY
================================================================================

Overall Performance:
  Total tests: 30
  Correct: 26 (86.7%)
  Incorrect: 4
  Low confidence: 3

Performance by Category:
  ✅ store_clear         : 4/4 (100.0%)
  ✅ query_clear         : 5/5 (100.0%)
  ✅ chat_clear          : 6/6 (100.0%)
  ✅ task_clear          : 3/3 (100.0%)
  ✅ list_clear          : 2/3 (66.7%)
  ⚠️  ambiguous          : 3/4 (75.0%)
  ✅ composite           : 2/2 (100.0%)

================================================================================
ASSESSMENT
================================================================================

✅ EXCELLENT - Intent detection is production-ready!

Target: ≥85% accuracy
Current: 86.7%
```

## Success Criteria

### Production Ready (✅)
- **Overall accuracy**: ≥85%
- **Clear cases**: ≥95%
- **Ambiguous cases**: ≥60% (acceptable for fallback strategy)

### Needs Improvement (⚠️)
- **Overall accuracy**: 75-85%
- Action: Refine prompts, add more examples

### Reconsider Strategy (❌)
- **Overall accuracy**: <75%
- Action: Use better model or hybrid approach (keywords + LLM)

## Interpreting Results

### High Accuracy (>85%)
✅ **Ready to implement Strategy 2**
- Intent detection is reliable
- Can proceed with Agent Zero implementation
- Minor prompt tuning may improve further

### Medium Accuracy (75-85%)
⚠️ **Needs prompt refinement**
- Core strategy is sound
- Improve prompt with:
  - More examples
  - Clearer disambiguation rules
  - Better entity extraction

### Low Accuracy (<75%)
❌ **Reconsider approach**
- May need:
  - Larger/better LLM model
  - Hybrid approach (keywords + LLM)
  - More training examples
  - Fine-tuned model

## Common Failure Patterns

### 1. MEMORY_QUERY vs CHAT Confusion
```
User: "¿Qué sabes de Barcelona?"
Expected: CHAT (fallback)
Detected: MEMORY_QUERY

Solution: Emphasize in prompt that ambiguous questions → CHAT
```

### 2. LIST_ADD False Positives
```
User: "Pan" (just a word)
Expected: LIST_ADD
Detected: CHAT

Solution: This is actually OK - better to ask "¿A qué lista?" than assume
```

### 3. Low Confidence on Clear Cases
```
User: "Recuérdame llamar a Juan"
Expected: TASK_CREATE (0.95)
Detected: TASK_CREATE (0.70)

Solution: Add more TASK_CREATE examples to prompt
```

## Next Steps After Testing

### If Accuracy ≥85%
1. ✅ Implement IntentDetector agent
2. ✅ Implement Agent Zero with routing
3. ✅ Test with real conversations
4. ✅ Monitor and iterate

### If Accuracy 75-85%
1. ⚠️ Analyze failures
2. ⚠️ Refine prompt (add examples, clarify rules)
3. ⚠️ Re-test
4. ⚠️ If still <85%, consider model upgrade

### If Accuracy <75%
1. ❌ Try better model (upgrade from qwen3:1.7b → qwen3:8b or llama3:8b)
2. ❌ Or implement hybrid (keywords + LLM)
3. ❌ Or use dedicated classification model

## Modifying the Test

### Add New Test Case

```python
TEST_CASES.append({
    "message": "Your test message here",
    "expected": "MEMORY_QUERY",  # or other intent
    "confidence_threshold": 0.85,
    "category": "query_clear",  # or custom category
    "notes": "Optional explanation"
})
```

### Adjust Confidence Thresholds

Lower thresholds for ambiguous cases:
```python
{
    "message": "¿Qué sabes de X?",
    "expected": "CHAT",
    "confidence_threshold": 0.50,  # Lower for ambiguous
    "category": "ambiguous"
}
```

### Test Different Models

In `test_intent_detection.py`:
```python
# Change model in .env or settings
# Then re-run test to compare
```

## Files Generated

- **data/intent_detection_test_results.json** - Detailed results in JSON format

Example structure:
```json
{
  "total": 30,
  "correct": 26,
  "incorrect": 4,
  "low_confidence": 3,
  "by_category": {
    "store_clear": {"total": 4, "correct": 4},
    "query_clear": {"total": 5, "correct": 5},
    ...
  },
  "failures": [
    {
      "message": "¿Qué sabes de Barcelona?",
      "expected": "CHAT",
      "detected": "MEMORY_QUERY",
      "confidence": 0.75,
      "category": "ambiguous"
    }
  ]
}
```

## Tips for Good Results

### 1. Clear Prompt Structure
- ✅ Use numbered categories
- ✅ Provide characteristics for each intent
- ✅ Include 2-3 examples per intent
- ✅ Add disambiguation rules

### 2. Emphasize Fallback Strategy
```
"Si hay duda entre MEMORY_QUERY y CHAT → elige CHAT"
```

### 3. Test Iteratively
1. Run test
2. Analyze failures
3. Adjust prompt
4. Re-run
5. Repeat until ≥85%

## Troubleshooting

### Test Fails to Run

```bash
# Check Python path
$env:PYTHONPATH="src"

# Check dependencies
pip install -r requirements.txt

# Check LLM service
# Make sure Ollama is running: ollama serve
```

### All Tests Fail

```bash
# Check .env configuration
cat .env | grep LLM

# Test LLM directly
python -c "from app.llm import LLMService; from app.config import get_settings; llm = LLMService(get_settings()); print(llm.generate('Hello'))"
```

### Low Accuracy on All Categories

1. **Check model**: Is qwen3:1.7b too small?
2. **Try larger model**: qwen3:8b or llama3:8b
3. **Check prompt**: Are instructions clear?
4. **Validate examples**: Do they match your use case?

## Questions?

If accuracy is good (≥85%), you're ready to implement!

If you need to adjust the prompt or add examples, edit the `build_intent_prompt()` function in the test file.

**Ready to run the test?**

```bash
$env:PYTHONPATH="src"; python tests/test_intent_detection.py
```
