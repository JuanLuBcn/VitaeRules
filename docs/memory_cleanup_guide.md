# Memory Cleanup Guide

## 🧹 Overview

The VitaeBot stores data in three locations:
1. **Short-term Memory (SQLite)** - Conversation history
2. **Long-term Memory (Chroma)** - Vector embeddings for notes, tasks, memories
3. **Storage Directory** - Runtime data and temporary files

## 📍 Data Locations

Based on your configuration (`.env` file):

```
data/
├── app.sqlite          # SQLite database (conversations)
├── chroma/            # Vector store (memories)
└── storage/           # Runtime files
```

## 🔧 Cleanup Scripts

### 1. Interactive Cleanup (Recommended)

**Script:** `scripts/purge_memory.py`

Safe, interactive cleanup with confirmations:

```bash
python scripts/purge_memory.py
```

**Features:**
- Shows what will be deleted
- Asks for confirmation before each step
- Provides detailed summary
- Safe for production environments

**Example Output:**
```
╔══════════════════════════════════════════════════════════════╗
║                  MEMORY PURGE UTILITY                        ║
║                                                              ║
║  This will DELETE ALL stored data:                          ║
║  • All conversation history                                 ║
║  • All notes and tasks                                      ║
║  • All memories                                             ║
╚══════════════════════════════════════════════════════════════╝

Are you sure you want to purge all memory? (yes/no): yes

🧹 Starting memory cleanup...
   ✓ Deleted 142 conversation messages
   ✓ Deleted 87 vector files
   ✓ Database cleaned successfully

✅ Memory cleanup complete!
```

---

### 2. Quick Cleanup (For Testing)

**Script:** `scripts/quick_purge.py`

Fast cleanup without confirmations:

```bash
python scripts/quick_purge.py
```

**Features:**
- No confirmations (instant)
- Perfect for rapid testing iterations
- Skips storage directory (preserves configs)

**Example Output:**
```
✅ Purged: 142 conversations, 87 vector files
```

---

### 3. Status Check

**Script:** `scripts/check_memory.py`

Verify memory status without deleting anything:

```bash
python scripts/check_memory.py
```

**Features:**
- Shows current memory usage
- Lists table row counts
- Counts vector store files
- No destructive operations

**Example Output:**
```
📊 MEMORY STATUS REPORT
================================================================================

🗄️  Short-Term Memory (SQLite)
   Database: data\app.sqlite
   Tables: 1
   • conversations: 0 rows

📚 Long-Term Memory (Vector Store)
   Directory: data\chroma
   Files: 0
   Directories: 0
   ✅ Vector store is empty (clean)

💾 Storage Directory
   Files: 0
   ✅ Storage is empty

✅ Status check complete!
```

---

## 🎯 Common Use Cases

### Starting Fresh After Testing

```bash
# Check current state
python scripts/check_memory.py

# Clean everything
python scripts/purge_memory.py

# Verify cleanup
python scripts/check_memory.py
```

### Rapid Testing Iterations

```bash
# Test cycle 1
python main.py
# ... test something ...

# Quick cleanup
python scripts/quick_purge.py

# Test cycle 2
python main.py
# ... test again ...
```

### Before Production Deployment

```bash
# Review what's stored
python scripts/check_memory.py

# Decide if cleanup needed
python scripts/purge_memory.py
```

---

## ⚠️ Important Notes

### What Gets Deleted

**Short-term Memory:**
- All conversation messages (user and bot)
- Chat history across all users
- Session context

**Long-term Memory:**
- All saved notes
- All created tasks
- All stored memories
- Vector embeddings
- Metadata and timestamps

**Storage:**
- Runtime files
- Temporary data
- (Optional - asks for confirmation)

### What Doesn't Get Deleted

- Configuration files (`.env`)
- Application code
- Log files (`data/trace.jsonl`)
- Database schema (tables remain, just empty)

### Irreversible Action

⚠️ **WARNING:** Memory cleanup is **PERMANENT**. There is no undo or recovery option.

Always:
1. Backup data if needed before cleanup
2. Use `check_memory.py` first to see what will be deleted
3. Use interactive mode (`purge_memory.py`) in production

---

## 🔍 Manual Cleanup (Alternative)

If you prefer manual cleanup:

### SQLite Database

```bash
# Connect to database
sqlite3 data/app.sqlite

# View tables
.tables

# Clear conversations
DELETE FROM conversations;

# Exit
.quit
```

### Vector Store

```bash
# Windows PowerShell
Remove-Item -Recurse -Force data\chroma
New-Item -ItemType Directory -Path data\chroma

# Linux/Mac
rm -rf data/chroma
mkdir data/chroma
```

### Storage Files

```bash
# Windows PowerShell
Remove-Item -Recurse -Force data\storage\*

# Linux/Mac
rm -rf data/storage/*
```

---

## 🧪 Testing Recommendations

### Before Running Tests

```bash
# Clean slate
python scripts/quick_purge.py

# Run tests
pytest tests/integration/

# Cleanup after tests
python scripts/quick_purge.py
```

### Development Workflow

```bash
# 1. Start with clean state
python scripts/check_memory.py

# 2. Test new feature
python main.py

# 3. Review what was stored
python scripts/check_memory.py

# 4. Clean before next iteration
python scripts/quick_purge.py
```

---

## 📊 Current Status (After Latest Cleanup)

```
✅ Short-term Memory: 0 conversations
✅ Long-term Memory: 0 memories
✅ Storage: Empty

Ready for fresh start! 🚀
```

---

## 🛠️ Troubleshooting

### Database Locked Error

If you get "database is locked":
1. Stop the bot (`Ctrl+C`)
2. Wait 5 seconds
3. Run cleanup again

### Permission Denied

If cleanup fails with permission errors:
```bash
# Windows: Run PowerShell as Administrator
# Linux/Mac: Use sudo if needed
```

### Cleanup Incomplete

If some data remains:
```bash
# Check status
python scripts/check_memory.py

# Try manual cleanup
# See "Manual Cleanup" section above
```

---

## 📝 Script Reference

| Script | Purpose | Confirmations | Speed | Use Case |
|--------|---------|---------------|-------|----------|
| `purge_memory.py` | Full cleanup | Yes | Moderate | Production, first-time cleanup |
| `quick_purge.py` | Fast cleanup | No | Fast | Testing, development |
| `check_memory.py` | Status check | N/A | Instant | Verification, monitoring |

---

## 🎓 Best Practices

1. **Always check first**: Use `check_memory.py` before cleanup
2. **Use interactive mode**: Safer for production environments
3. **Regular cleanup**: Clean between major testing phases
4. **Backup if needed**: Export important data before cleanup
5. **Verify after**: Run `check_memory.py` to confirm

---

*Last cleanup: October 22, 2025*
*Status: All memory cleared - ready for fresh start! ✅*
