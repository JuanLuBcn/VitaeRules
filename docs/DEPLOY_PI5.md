# 🚀 Deploying minimax-m2:cloud to Raspberry Pi 5

## Summary
The bot is now working flawlessly with **minimax-m2:cloud** model! This model correctly calls tools instead of hallucinating answers like qwen3-coder did.

## What Changed
- ✅ Fixed LLM temperature (0.1 for better tool calling)
- ✅ Enhanced agent prompts with MANDATORY tool-calling instructions
- ✅ Fixed tool schema validation errors
- ✅ Switched from qwen3-coder:480b-cloud to minimax-m2:cloud
- ✅ **Result:** Bot now correctly searches memory and returns "JuanLu" instead of hallucinating "Carlos"

## Manual Deployment Steps

### 1. SSH into your Raspberry Pi 5
```bash
ssh core@homeassistant.local
# or whatever your Pi5 address is
```

### 2. Navigate to VitaeRules directory
```bash
cd VitaeRules
```

### 3. Pull latest code changes
```bash
git pull origin main
```

### 4. Stop the current container
```bash
docker compose down
# or
docker stop vitaerules
```

### 5. Update .env file with new model
```bash
# Edit .env file
nano .env

# Change the line:
OLLAMA_MODEL=minimax-m2:cloud

# Save with Ctrl+X, then Y, then Enter
```

### 6. Pull the minimax-m2 model on Pi5 (if not already)
```bash
ollama pull minimax-m2:cloud
```

### 7. Rebuild Docker image
**Important:** The Dockerfile copies .env into the image, so you MUST rebuild after changing .env:
```bash
docker compose build --no-cache
```

### 8. Start the container
```bash
docker compose up -d
```

### 9. Verify it's running
```bash
docker ps | grep vitaerules
docker logs -f vitaerules
```

## Testing

Send a message to your Telegram bot:
- "Sabes como me llamo?"
- Expected: Bot should use memory_search tool and respond "JuanLu"
- Previous behavior: qwen3-coder would hallucinate "Carlos" without calling tools

## Troubleshooting

### If container won't start:
```bash
docker logs vitaerules
```

### If Ollama connection issues:
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Check OLLAMA_BASE_URL in .env
cat .env | grep OLLAMA_BASE_URL
```

### To restart after changes:
```bash
docker compose restart
```

## Performance Notes

- **minimax-m2:cloud** is faster than qwen3-coder:480b-cloud
- Tool calling is much more reliable
- Temperature set to 0.1 for consistent tool usage

## Files Changed

1. `src/app/llm/crewai_llm.py` - Temperature 0.7 → 0.1
2. `src/app/tools/memory_search_tool.py` - Added explicit schema with optional fields
3. `src/app/crews/search/memory_searcher.py` - Enhanced anti-hallucination prompts
4. `src/app/crews/search/crew.py` - Strengthened MANDATORY tool-calling instructions
5. `.env` - Changed OLLAMA_MODEL to minimax-m2:cloud (not in git, manual update needed)

## Success Criteria ✅

- [x] Bot responds to Telegram messages
- [x] memory_search tool is actually called (check logs for "Tool Execution")
- [x] Returns correct data from ChromaDB ("JuanLu", not "Carlos")
- [x] No hallucinated dates from 2023
- [x] Response includes real memory content

---

**Last Updated:** December 12, 2025
**Model:** minimax-m2:cloud
**Status:** ✅ Ready for production deployment
