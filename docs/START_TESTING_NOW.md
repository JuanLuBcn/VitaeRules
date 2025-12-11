# ✅ Bot is Ready! - Next Steps

## Current Status

🎉 **SUCCESS!** The VitaeRules bot is now fully configured and ready for testing.

**What's Working**:
- ✅ Bot starts without errors
- ✅ Ollama LLM connected (qwen3:1.7b)
- ✅ MediaHandler initialized
- ✅ Telegram handlers registered
- ✅ 4 tools ready (Task, List, Temporal, Memory)
- ✅ Database ready
- ✅ Media storage configured

**Optional**:
- ⚠️ Whisper not installed (voice transcription unavailable - not critical for now)

---

## Quick Start: Begin Testing NOW!

### Step 1: Start the Bot (1 minute)

Open a PowerShell terminal and run:

```powershell
cd C:\Users\coses\Documents\GitRepos\VitaeRules
$env:PYTHONPATH="src"
python -m app.main
```

**Expected Output**:
```
🚀 Starting VitaeRules Telegram Bot...
✓ LLM Service: ollama (qwen3:1.7b)
✓ Tools registered: 4
✅ Bot is ready! Waiting for messages...
MediaHandler initialized at data\storage\media
VitaeBot initialized with media support
telegram_bot_running
```

**Keep this terminal open!**

---

### Step 2: Open Telegram (1 minute)

1. Open Telegram (mobile or desktop)
2. Search for your bot (check `.env` for bot username)
3. Start a conversation with `/start`

---

### Step 3: Run Quick Smoke Tests (5 minutes)

#### Test 1: Simple Text ✅
```
You: Add milk to shopping list

Bot: ✅ Agregué 'milk' a la lista

You: Show my shopping list

Bot: 🛒 Lista de la compra:
     ⬜ milk
     1 elemento(s)
```

**Status**: ⬜ Not tested yet

---

#### Test 2: Photo + Shopping List 📷
```
1. Take a photo of any item (e.g., eggs, bread)
2. Send to bot with caption: "Add eggs to shopping list"

Expected:
Bot: 📷 Photo saved!
     ✅ Agregué 'eggs' a la lista 📷

You: Show shopping list

Bot: 🛒 Lista de la compra:
     ⬜ milk
     ⬜ eggs 📷
     2 elemento(s)
```

**Status**: ⬜ Not tested yet

---

#### Test 3: Document 📄
```
1. Send any .pdf or .txt file
2. Caption: "Save this document"

Expected:
Bot: 📄 Document saved!
     💾 ¿Guardar esta nota?
     
You: Yes

Bot: 💾 Nota guardada con éxito! 📄
```

**Status**: ⬜ Not tested yet

---

#### Test 4: Location 📍
```
1. Tap location button in Telegram
2. Share current location
3. Message: "I'm at the office"

Expected:
Bot: 📍 Location saved!
     💾 Note created: I'm at the office
```

**Status**: ⬜ Not tested yet

---

## If Everything Works...

**Congratulations!** 🎉 The media integration is working!

### Next: Full Testing (1-2 hours)

Open and follow:
- **Detailed Plan**: `docs/task6_testing_plan.md`
- **User Scenarios**: `docs/media_user_scenarios.md`

Test all phases:
1. ✅ Basic Media Input (15 min)
2. ✅ Agent Routing Accuracy (20 min)
3. ✅ Enrichment Conversations (30 min)
4. ✅ Display & Retrieval (15 min)
5. ✅ Edge Cases (20 min)
6. ✅ Performance & Logs (10 min)

---

## If Something Doesn't Work...

### Bot Won't Start

**Check**:
```powershell
# Is Ollama running?
netstat -ano | findstr :11434

# Should show: TCP 127.0.0.1:11434 ... LISTENING

# If not, start Ollama:
ollama serve
```

**Check**:
```powershell
# Is Python environment correct?
python --version  # Should be 3.11 or 3.12

# Are dependencies installed?
pip list | findstr "telegram|crewai|langchain"
```

---

### Bot Starts but Doesn't Respond

**Check**:
1. Is bot token correct in `.env`?
2. Did you `/start` the conversation?
3. Check logs for errors:
   ```powershell
   Get-Content data/trace.jsonl -Tail 20
   ```

---

### Photo Doesn't Save

**Check**:
```powershell
# Does media folder exist?
Get-ChildItem data/storage/media

# Check logs for media errors:
Get-Content data/trace.jsonl | Select-String "media|photo"
```

---

### Voice Transcription Not Working

**This is expected!** Whisper isn't installed yet.

**To enable voice transcription**:
```powershell
pip install openai-whisper faster-whisper
```

**Note**: Voice files will still save, just without transcription text.

---

## Quick Commands Reference

### View Logs
```powershell
# Last 50 lines
Get-Content data/trace.jsonl -Tail 50

# Real-time monitoring
Get-Content data/trace.jsonl -Wait -Tail 10

# Errors only
Get-Content data/trace.jsonl | Select-String "ERROR"

# Media events
Get-Content data/trace.jsonl | Select-String "media|photo|voice|document"
```

### Check Database
```powershell
sqlite3 data/app.sqlite

# View tasks with media
SELECT id, title, media_path FROM tasks WHERE media_path IS NOT NULL;

# View list items with media
SELECT id, text, media_path FROM list_items WHERE media_path IS NOT NULL;

# Exit
.quit
```

### Check Media Files
```powershell
# All media
Get-ChildItem data/storage/media -Recurse

# Photos only
Get-ChildItem data/storage/media -Recurse -Include *.jpg,*.png

# Voice only
Get-ChildItem data/storage/media -Recurse -Include *.ogg,*.mp3

# Documents only
Get-ChildItem data/storage/media -Recurse -Include *.pdf,*.txt
```

---

## Testing Checklist

### Basic Functionality
- [ ] Bot starts successfully
- [ ] Simple text messages work
- [ ] Photo upload works
- [ ] Photo shows 📷 emoji
- [ ] Document upload works
- [ ] Document shows 📄 emoji
- [ ] Location sharing works
- [ ] Location shows 📍 emoji

### Agent Routing
- [ ] "Add X to list" → LIST agent
- [ ] "Remind me to X" → TASK agent
- [ ] "Save this" → NOTE agent
- [ ] "What's on my list?" → QUERY agent

### Enrichment
- [ ] Task creation asks "when?"
- [ ] Media preserved through questions
- [ ] Final task has media_path

### Display
- [ ] Shopping list shows emojis
- [ ] Task list shows emojis
- [ ] Success messages show emojis

### Database
- [ ] Tasks table has media_path
- [ ] Lists table has media_path
- [ ] Files exist in media folder

---

## When You're Done Testing

### Document Results

Create a summary:
```markdown
# Task 6 Results

## Tests Passed ✅
- Basic text: ✅
- Photo upload: ✅
- Document upload: ✅
- Location sharing: ✅
- Agent routing: ✅
- Enrichment: ✅
- Display: ✅

## Issues Found 🐛
1. [Describe any issues]

## Performance ⚡
- Photo upload: X seconds
- Bot response: Y seconds

## Next Steps
- Fix issue #1
- Start Task 7: Prompt Refinement
```

### Update Todo List

Mark Task 6 complete when:
- [x] All 4 media types tested
- [x] Agent routing validated
- [x] Enrichment works with media
- [x] Emoji display confirmed
- [x] Issues documented

---

## You're All Set! 🚀

**Current**: Bot configured and ready  
**Next**: Start bot and test!  
**Time**: ~5 min for quick tests, ~2 hours for full testing  
**Goal**: Validate the entire media pipeline works end-to-end

**Let's go!** Send that first message and see the magic happen! ✨

---

## Need Help?

**Check Documentation**:
- `docs/task6_testing_plan.md` - Full testing scenarios
- `docs/media_user_scenarios.md` - Expected user experience
- `docs/task6_session1_summary.md` - What we've done so far

**Common Issues**:
- Bot not responding → Check `.env` token
- Photos not saving → Check media folder permissions
- Voice not transcribing → Whisper not installed (optional)

**Success**: Bot responds to messages and saves media files! 🎉
