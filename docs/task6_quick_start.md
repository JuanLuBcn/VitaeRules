# Quick Start Guide - Task 6 Testing

## Step 1: Start the Bot

### Option A: Terminal
```powershell
# Make sure you're in the repo root
cd C:\Users\coses\Documents\GitRepos\VitaeRules

# Activate virtual environment (if not already)
.\.venv\Scripts\Activate.ps1

# Start the bot
python -m src.app.main
```

### Option B: VS Code
1. Open integrated terminal
2. Run: `python -m src.app.main`
3. Watch for: "Bot started successfully"

---

## Step 2: Open Telegram

1. Open Telegram app (mobile or desktop)
2. Find your bot: Search for your bot name
3. Start conversation: `/start`

---

## Step 3: Quick Smoke Tests

### Test A: Photo + Shopping List (2 min)
```
1. Take photo of any item (milk, eggs, etc.)
2. Send to bot with caption: "Add milk to shopping list"
3. ✅ Check response has 📷 emoji
4. Send: "Show my shopping list"
5. ✅ Check list shows: "⬜ milk 📷"
```

**Expected Output**:
```
Bot: 📷 Photo saved!
     ✅ Agregué 'milk' a la lista 📷

You: Show my shopping list

Bot: 🛒 Lista de la compra:
     ⬜ milk 📷
     1 elemento(s)
```

---

### Test B: Voice Note Task (3 min)
```
1. Hold voice button in Telegram
2. Say clearly: "Remind me to call mom tomorrow"
3. Release and send
4. Wait for transcription (~5 seconds)
5. ✅ Check task created
6. Send: "What are my tasks?"
7. ✅ Check shows: "⬜ Call mom 🎤"
```

**Expected Output**:
```
Bot: 🎤 Transcribing your voice message...

     🎤 Voice transcribed:
     "Remind me to call mom tomorrow"
     
     ✅ Creé la tarea: **Call mom** 🎤
     📅 Fecha: Tomorrow

You: What are my tasks?

Bot: 📋 Tus Tareas
     
     Pendientes:
     ⬜ Call mom 🎤
        📅 Fecha: Tomorrow
```

---

### Test C: Simple Text (Baseline) (1 min)
```
1. Send: "Add bread to shopping list"
2. ✅ Check works without media
3. Send: "Show shopping list"
4. ✅ Check shows both items:
   - milk 📷
   - bread (no emoji)
```

**Expected Output**:
```
Bot: ✅ Agregué 'bread' a la lista

You: Show shopping list

Bot: 🛒 Lista de la compra:
     ⬜ milk 📷
     ⬜ bread
     2 elemento(s)
```

---

## Step 4: Detailed Testing

### Follow the full testing plan:
📄 See: `docs/task6_testing_plan.md`

**Phases**:
1. ✅ Basic Media Input (15 min)
2. ✅ Agent Routing (20 min)
3. ✅ Enrichment Flow (30 min)
4. ✅ Display & Retrieval (15 min)
5. ✅ Edge Cases (20 min)
6. ✅ Performance & Logs (10 min)

**Total**: ~2 hours

---

## Step 5: Document Issues

### While testing, note:
- ✅ **What worked well**
- ⚠️ **What needs improvement**
- 🐛 **Bugs found**
- 💡 **UX ideas**

### Where to document:
1. Fill in sections in `task6_testing_plan.md`
2. Create issue list for Task 7
3. Note prompt improvements needed

---

## Common Issues & Quick Fixes

### Issue: Bot doesn't respond
**Check**:
```powershell
# Is Ollama running?
ollama list

# Is bot running?
tasklist | findstr python

# Check logs
Get-Content data/trace.jsonl -Tail 20
```

**Fix**: Restart bot or Ollama

---

### Issue: Voice transcription fails
**Check**:
```powershell
# Is Whisper installed?
python -c "import whisper; print('OK')"
```

**Fix**: 
```powershell
pip install openai-whisper
```

---

### Issue: Photo not saving
**Check**:
1. Look in `media/` folder
2. Check permissions
3. Check logs for errors

**Fix**: Create media folder manually:
```powershell
mkdir media
```

---

### Issue: Wrong agent routing
**Note for Task 7**:
- Document the message
- What agent it went to
- What agent it should have gone to
- Add to prompt improvement list

---

## Quick Commands

### View Recent Logs
```powershell
# Last 50 lines
Get-Content data/trace.jsonl -Tail 50

# Filter for errors
Get-Content data/trace.jsonl | Select-String "ERROR"

# Filter for media
Get-Content data/trace.jsonl | Select-String "media"
```

### Check Database
```powershell
# Open SQLite
sqlite3 data/app.sqlite

# Check tasks with media
SELECT id, title, media_path FROM tasks WHERE media_path IS NOT NULL;

# Check lists with media
SELECT id, text, media_path FROM list_items WHERE media_path IS NOT NULL;

# Exit
.quit
```

### Check Media Files
```powershell
# List all photos
Get-ChildItem media/ -Recurse -Include *.jpg, *.png

# List all voice
Get-ChildItem media/ -Recurse -Include *.ogg

# List all documents
Get-ChildItem media/ -Recurse -Include *.pdf
```

---

## Success Indicators

### ✅ Green Flags (Everything Working)
- Bot responds within 3 seconds
- Photos upload and show 📷
- Voice transcribes and shows 🎤
- Tasks/lists display correctly
- Enrichment conversations flow naturally
- Media files exist in `media/` folder
- Database has media_path entries

### ⚠️ Yellow Flags (Needs Attention)
- Slow responses (>5 seconds)
- Routing to wrong agent occasionally
- Transcription inaccurate
- Enrichment questions awkward
- Some emojis missing

### 🚨 Red Flags (Critical Issues)
- Bot crashes
- Photos don't save
- Voice transcription always fails
- Agent routing consistently wrong
- Database errors
- Media files corrupted

---

## After Testing

### Create Summary Document
```markdown
# Task 6 Results

## What Worked
- [List successes]

## Issues Found
### Critical
- [List critical bugs]

### Minor
- [List minor issues]

## Prompt Improvements for Task 7
- [List prompt changes needed]

## Performance Metrics
- Photo upload: X seconds
- Voice transcription: Y seconds
- Task creation: Z seconds

## Next Steps
- Fix critical issues
- Start Task 7: Prompt Refinement
```

---

## Ready to Start?

1. ✅ Ollama running
2. ✅ Models available
3. ✅ Testing plan ready
4. ✅ Bot code complete
5. ⏳ **Start the bot**: `python -m src.app.main`
6. ⏳ **Open Telegram**
7. ⏳ **Begin testing!**

**Estimated Time**: 2 hours
**Goal**: Complete Phase 3 is 50% done, let's test it! 🚀
