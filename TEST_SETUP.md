# LLM Performance Test - Setup Guide

## Models to Test

### Ollama Models (Local)
These models run locally via Ollama:

```powershell
# Pull models (run these first)
ollama pull gemma2:2b
ollama pull qwen2.5:1.5b
ollama pull llama3.2:3b
ollama pull deepseek-r1:1.5b
```

### MiniMax (Cloud)
**minimax-m2:cloud** is NOT available in Ollama. MiniMax is a Chinese AI company with cloud API access.

To use MiniMax, you would need:
1. API key from MiniMax (https://www.minimaxi.com/)
2. Integration via their API (not Ollama)
3. Modify the test script to support external API calls

**Recommendation**: Skip MiniMax for this local test, or add it separately if you have API access.

## Running the Test

1. **Ensure Ollama is running**:
   ```powershell
   # Check if Ollama is running
   curl http://localhost:11434/api/version
   ```

2. **Pull all models** (this may take a while):
   ```powershell
   ollama pull gemma2:2b
   ollama pull qwen2.5:1.5b  
   ollama pull llama3.2:3b
   ollama pull deepseek-r1:1.5b
   ```

3. **Activate virtual environment**:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

4. **Run the test**:
   ```powershell
   python test_llm_performance.py
   ```

## Test Cases

The test includes 20 diverse messages:
- **8 SEARCH** (questions): "What is in my shopping list?", "Dónde dejé las llaves?", etc.
- **12 ACTION** (statements/commands): "Hoy fuimos a la oficina", "Hello", "Add tomatoes", etc.

## Expected Output

The test will show:
1. **Real-time progress** for each model and test case
2. **Per-model results**: Accuracy %, average/min/max time
3. **Summary comparison table**: All models ranked
4. **Best recommendations**: Accuracy winner, speed winner, best balance
5. **Detailed JSON file**: Full results saved to `llm_test_results.json`

## Estimated Time

- Each test case: 2-10 seconds (depending on model)
- 20 test cases × 4 models = ~5-15 minutes total

## Model Sizes

- **gemma2:2b**: ~1.6 GB (fastest, less accurate)
- **qwen2.5:1.5b**: ~900 MB (smallest, fastest)
- **llama3.2:3b**: ~2 GB (balanced)
- **deepseek-r1:1.5b**: ~900 MB (reasoning-focused)

## Alternative: Test Subset

To test faster, you can modify the script to test fewer cases:
```python
# In test_llm_performance.py, line 31-50
# Comment out some TEST_CASES to reduce test time
```
