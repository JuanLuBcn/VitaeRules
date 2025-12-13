# 🔧 Troubleshooting Pi5 Deployment Issues

## Issue 1: Memory Search Not Finding Data

### Symptom
Bot says "no tengo esa información disponible" even though data exists in ChromaDB.

### Possible Causes
1. **ChromaDB not mounted properly** - Volume might not be persisting
2. **Ollama embedding model not accessible** - Memory search needs embeddings
3. **Database path mismatch**

### Check Commands on Pi5

```bash
# 1. Check if ChromaDB data exists
docker exec vitaerules ls -la /app/data/chroma

# 2. Check logs for embedding errors
docker logs vitaerules | grep -i "embedding\|chroma\|connection"

# 3. Verify Ollama is accessible from container
docker exec vitaerules curl http://localhost:11434/api/tags

# 4. Check if memory search tool is being called
docker logs vitaerules | grep -i "memory_search\|Tool Execution"
```

### Debug Memory Search

Run this inside the container:
```bash
# Enter container
docker exec -it vitaerules bash

# Test memory search directly
python -c "
import sys
sys.path.insert(0, '/app/src')
from app.tools.memory_search_tool import MemorySearchTool
tool = MemorySearchTool()
result = tool._run('nombre de la hija')
print(result)
"
```

## Issue 2: Memory Save/Capture Failing

### Symptom
Bot says "hubo un problema técnico con el formato de almacenamiento" when trying to save new memories.

### Common Error: `'person' is not a valid MemorySection`

**Root Cause**: Tool schema had invalid enum values (`person`, `project`, `reference`, `idea`) that don't exist in the actual `MemorySection` enum.

**Solution**: Fixed in commit that syncs tool schema with valid enum values:
- `event` - Scheduled events with dates
- `note` - Personal info, facts, general notes (use this for people info)
- `diary` - Diary entries
- `task` - Todos
- `list` - Lists
- `reminder` - Reminders
- `conversation` - Conversations

Tool now falls back to `note` if an invalid section is provided.

### Other Possible Causes
1. **Pydantic validation error** - Date format or field validation
2. **ChromaDB write permissions**
3. **Capture crew tool failure**

### Check Commands

```bash
# 1. Check CaptureCrew logs
docker logs vitaerules | grep -i "capture\|save\|store"

# 2. Check write permissions
docker exec vitaerules ls -la /app/data

# 3. Test memory storage directly
docker exec vitaerules python -c "
import sys
sys.path.insert(0, '/app/src')
from app.memory.api import MemoryService
from app.memory.schemas import MemoryCreate

service = MemoryService()
memory = MemoryCreate(
    title='Test',
    content='Test content',
    tags=['test']
)
result = service.create_memory(memory)
print('SUCCESS:', result)
"
```

## Issue 3: Data Not Persisting Between Restarts

### Check Volume

```bash
# List all volumes
docker volume ls

# Inspect vitae_data volume
docker volume inspect vitae_data

# Check what's inside the volume
docker run --rm -v vitae_data:/data alpine ls -la /data
```

## Quick Health Check Script

Save this as `check_bot_health.sh` on Pi5:

```bash
#!/bin/bash
echo "=== VitaeRules Health Check ==="

echo -e "\n1. Container Status:"
docker ps | grep vitaerules || echo "❌ Container not running"

echo -e "\n2. Ollama Connectivity:"
docker exec vitaerules curl -s http://localhost:11434/api/tags | grep -q "models" && echo "✅ Ollama accessible" || echo "❌ Ollama not accessible"

echo -e "\n3. ChromaDB Data:"
docker exec vitaerules ls /app/data/chroma 2>/dev/null && echo "✅ ChromaDB data exists" || echo "❌ No ChromaDB data"

echo -e "\n4. Recent Errors:"
docker logs --tail 50 vitaerules | grep -i "error\|failed\|exception" | tail -5

echo -e "\n5. Memory Stats:"
docker exec vitaerules python -c "
import sys
sys.path.insert(0, '/app/src')
from app.memory.api import MemoryService
service = MemoryService()
# This will fail if there's a connection issue
print('Memory service initialized successfully')
" 2>&1
```

Make it executable:
```bash
chmod +x check_bot_health.sh
./check_bot_health.sh
```

## Common Fixes

### Fix 1: Restart with fresh ChromaDB
```bash
docker stop vitaerules
docker rm vitaerules
# Backup old data
docker run --rm -v vitae_data:/data -v $(pwd):/backup alpine tar czf /backup/vitae_backup.tar.gz /data
# Start fresh
docker volume rm vitae_data
# Rebuild and start
docker build -t vitaerules:latest .
docker run -d \
  --name vitaerules \
  --restart unless-stopped \
  --network host \
  -e APP_ENV=prod \
  -e OLLAMA_BASE_URL=http://localhost:11434 \
  -v vitae_data:/app/data \
  vitaerules:latest
```

### Fix 2: Verify .env was copied into image
```bash
docker exec vitaerules cat /app/.env | grep OLLAMA_MODEL
# Should show: OLLAMA_MODEL=minimax-m2:cloud
```

### Fix 3: Re-add test memories
```bash
# Copy the check_memories.py script to Pi5
# Run it inside container to re-populate test data
docker cp check_memories.py vitaerules:/app/
docker exec vitaerules python check_memories.py
```

## Expected Behavior

When working correctly, logs should show:
```
Tool Execution
Tool: memory_search
Arguments: {"query": "hija nombre", "limit": 5}
Tool Output: Found 1 memories: 1. **Children Information** ...
```

## Getting Help

If issues persist, collect this info:

```bash
# Full logs
docker logs vitaerules > vitaerules_logs.txt

# Environment check
docker exec vitaerules env | grep OLLAMA > env_check.txt

# Volume contents
docker exec vitaerules find /app/data -type f > data_files.txt
```

Then share these files for debugging.
