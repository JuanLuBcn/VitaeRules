# Task 6: Real LLM Testing Plan

## Objective
Test the complete media pipeline end-to-end with Ollama to validate:
- Agent routing with media messages
- Media storage and retrieval
- Enrichment conversations with media
- Display of media indicators
- Error handling and edge cases

## Environment Setup

### Current Configuration
- **LLM Backend**: Ollama
- **Model**: qwen3:1.7b
- **Ollama URL**: http://localhost:11434
- **Available Models**: llama3.2:1b, llama3.2:latest, qwen3:8b, deepseek-r1:1.5b
- **Telegram Bot Token**: Configured in .env

### Prerequisites
- ✅ Ollama running
- ✅ Models downloaded
- ✅ Media services implemented
- ✅ Database schema ready
- ⏳ Bot running (will start)

---

## Test Suite

### Phase 1: Basic Media Input (15 min)

#### Test 1.1: Photo with Caption
**Input**: Photo + "Add milk to shopping list"

**Expected Flow**:
1. Telegram handler downloads photo
2. MediaHandler stores → `media/user_XXX/photos/photo_*.jpg`
3. Orchestrator extracts: `MediaReference(type="photo", ...)`
4. Routes to ListAgent (LIST intent)
5. ListAgent adds item with media_reference
6. Success message: "✅ Agregué 'milk' a la lista 📷"

**Validation**:
- ✅ Photo file exists in media folder
- ✅ Database has media_path
- ✅ Emoji shows in confirmation
- ✅ Query shows emoji in list

**Test Command** (in bot):
```
1. Send photo of milk
2. Caption: "Add milk to shopping list"
3. Wait for response
4. Query: "Show my shopping list"
```

---

#### Test 1.2: Voice Note Task
**Input**: Voice message "Remind me to call mom tomorrow"

**Expected Flow**:
1. Telegram handler downloads .ogg file
2. WhisperService transcribes (if available)
3. MediaHandler stores voice file
4. Orchestrator extracts MediaReference
5. Routes to TaskAgent (TASK intent)
6. TaskAgent creates task with media
7. May trigger enrichment for "when?"

**Validation**:
- ✅ Voice file stored
- ✅ Transcription accurate
- ✅ Task created with media_path
- ✅ 🎤 emoji in task list

**Test Command**:
```
1. Send voice note saying: "Remind me to call mom tomorrow"
2. Wait for transcription
3. Check task creation
4. Query: "What are my tasks?"
```

---

#### Test 1.3: Document Note
**Input**: PDF file + "Contract for review"

**Expected Flow**:
1. Download and store document
2. Route to NoteAgent
3. Create memory with media
4. Confirmation with 📄

**Validation**:
- ✅ Document stored
- ✅ Memory created
- ✅ Searchable later

**Test Command**:
```
1. Send test.pdf
2. Caption: "Contract for review"
3. Confirm save
4. Search: "contract"
```

---

#### Test 1.4: Location Share
**Input**: Location + "I'm at the office"

**Expected Flow**:
1. Extract coordinates
2. Route to NoteAgent
3. Store with coordinates
4. No file storage (just coords)

**Validation**:
- ✅ Coordinates saved
- ✅ Note created
- ✅ Searchable by location

---

### Phase 2: Agent Routing Accuracy (20 min)

#### Test 2.1: LIST Intent with Media
**Test Cases**:
```
✅ Photo + "Add to shopping list"
✅ Photo + "Put this on my grocery list"
✅ Voice + "Add bread to the list"
✅ Document + "Add to reading list"
```

**Expected**: All route to ListAgent

**Metrics**:
- Routing accuracy: __/4 correct
- Media preserved: Yes/No
- Display works: Yes/No

---

#### Test 2.2: TASK Intent with Media
**Test Cases**:
```
✅ Voice + "Remind me to call mom"
✅ Photo + "Remember to buy this"
✅ Document + "Review before Monday"
✅ Location + "Pick up package here"
```

**Expected**: All route to TaskAgent

**Metrics**:
- Routing accuracy: __/4 correct
- Media preserved: Yes/No
- Display works: Yes/No

---

#### Test 2.3: NOTE Intent with Media
**Test Cases**:
```
✅ Photo + "Save this for later"
✅ Voice + "Note: Important idea"
✅ Document + "Keep this contract"
✅ Location + "Visited this place"
```

**Expected**: All route to NoteAgent

**Metrics**:
- Routing accuracy: __/4 correct
- Media preserved: Yes/No
- Searchable: Yes/No

---

#### Test 2.4: QUERY Intent
**Test Cases**:
```
✅ "What's on my shopping list?"
✅ "Show my tasks"
✅ "Find notes about contracts"
✅ "What did I save yesterday?"
```

**Expected**: Correct retrieval with media indicators

---

### Phase 3: Enrichment with Media (30 min)

#### Test 3.1: Task + When Enrichment
**Input**: Voice "Remind me to call mom"

**Expected Conversation**:
```
Bot: 🎤 Voice transcribed: "Remind me to call mom"
     ✅ Perfecto, crearé la tarea: **Call mom**
     
     📅 ¿Cuándo quieres que te lo recuerde?
     💡 Por ejemplo: "mañana a las 9", "el viernes", "en 2 horas"

User: Tomorrow at 9am

Bot: ¡Perfecto! 📅 Mañana a las 9am
     ✅ Creé la tarea 'Call mom' 🎤
```

**Validation**:
- ✅ Media preserved through enrichment
- ✅ Multi-turn conversation works
- ✅ Final task has media_path
- ✅ due_at extracted correctly

---

#### Test 3.2: Task + Who Enrichment
**Input**: Photo + "Buy birthday gift"

**Expected Conversation**:
```
Bot: 📷 Photo saved!
     ✅ Crearé la tarea: **Buy birthday gift**
     
     👤 ¿Para quién es este regalo?

User: For Sarah

Bot: ¡Perfecto! 👤 Para Sarah
     ✅ Creé la tarea 'Buy birthday gift' 📷
```

**Validation**:
- ✅ Media through enrichment
- ✅ People context saved
- ✅ Searchable: "tasks for Sarah"

---

#### Test 3.3: List + Which List Enrichment
**Input**: Photo + "Add this"

**Expected Conversation**:
```
Bot: 📷 Photo saved!
     
     📋 ¿A qué lista quieres agregarlo?
     💡 Listas disponibles: Shopping, Reading, Todo

User: Shopping

Bot: ✅ Agregué el item a 'Shopping' 📷
```

**Validation**:
- ✅ Media preserved
- ✅ List disambiguation works
- ✅ Item in correct list

---

### Phase 4: Display & Retrieval (15 min)

#### Test 4.1: Mixed Media List
**Setup**: Create list with multiple media types
```
1. Add "milk" (no media)
2. Add photo of eggs
3. Add voice note "bread"
4. Add document "recipe.pdf"
```

**Query**: "Show my shopping list"

**Expected Display**:
```
🛒 Lista de la compra:

⬜ milk
⬜ eggs 📷
⬜ bread 🎤
⬜ recipe 📄

4 elemento(s)
```

**Validation**:
- ✅ Each emoji correct
- ✅ No emoji for plain text
- ✅ Clean formatting

---

#### Test 4.2: Task List with Media
**Setup**: Create tasks with different media
```
1. Voice: "Call mom tomorrow"
2. Photo: "Buy this gift"
3. Plain: "Finish report"
```

**Query**: "What are my tasks?"

**Expected Display**:
```
📋 Tus Tareas

Pendientes:
⬜ Call mom 🎤
   📅 Fecha: Tomorrow

⬜ Buy this gift 📷

⬜ Finish report
```

---

#### Test 4.3: Search with Media
**Query**: "Find all items with photos"

**Expected**: Should retrieve and display items with 📷

**Query**: "Show voice notes"

**Expected**: Items with 🎤

---

### Phase 5: Edge Cases (20 min)

#### Test 5.1: Photo Without Caption
**Input**: Photo only (no text)

**Expected**: 
- Bot asks: "¿Qué quieres hacer con esta foto?"
- Or creates note with default text
- Media still saved

---

#### Test 5.2: Voice Without Whisper
**Setup**: Stop Whisper service (simulate failure)

**Input**: Voice message

**Expected**:
- Fallback message: "[Voice message - transcription unavailable]"
- File still saved
- User can still use it

---

#### Test 5.3: Large File
**Input**: 100MB file

**Expected**:
- Error: "File too large (max 50MB)"
- Graceful rejection

---

#### Test 5.4: Unsupported File Type
**Input**: .exe file

**Expected**:
- Stored as generic document
- 📎 emoji (fallback)

---

#### Test 5.5: Multiple Media Types
**Input**: Photo + Document in same message (if possible)

**Expected**:
- Handle first or ask which to use
- Or store both separately

---

### Phase 6: Performance & Logging (10 min)

#### Test 6.1: Response Times
**Measure**:
- Photo upload → confirmation: __s
- Voice transcription: __s
- Task creation with enrichment: __s
- Query with media: __s

**Targets**:
- Photo: < 3s
- Voice: < 5s (depends on Whisper)
- Enrichment: < 2s per turn
- Query: < 2s

---

#### Test 6.2: Log Inspection
**Check logs** for:
- ✅ Media type detection
- ✅ File storage paths
- ✅ Agent routing decisions
- ✅ Enrichment flows
- ⚠️ Any errors or warnings

**Log file**: `data/trace.jsonl`

---

#### Test 6.3: Database Verification
**SQL Queries**:
```sql
-- Check media paths
SELECT id, title, media_path, metadata 
FROM tasks 
WHERE media_path IS NOT NULL;

-- Check list items with media
SELECT id, text, media_path, metadata 
FROM list_items 
WHERE media_path IS NOT NULL;

-- Check memory items
SELECT id, content, media_type, media_path 
FROM memory_items 
WHERE media_path IS NOT NULL OR coordinates IS NOT NULL;
```

---

## Success Criteria

### Must Pass (Critical)
- ✅ All 4 media types upload and store correctly
- ✅ Agent routing accuracy > 90%
- ✅ Media preserved through enrichment conversations
- ✅ Emoji indicators display correctly
- ✅ Files accessible and not corrupted
- ✅ Database integrity (no null errors)

### Should Pass (Important)
- ✅ Whisper transcription works (if available)
- ✅ Response times under targets
- ✅ Error messages user-friendly
- ✅ Edge cases handled gracefully
- ✅ Logs show clear trace of operations

### Nice to Have
- ✅ Multiple media in one message
- ✅ Thumbnail generation for photos
- ✅ Search by media type
- ✅ Media cleanup on item deletion

---

## Issues Found

### Critical Issues
_(Fill during testing)_

**Example**:
- [ ] Issue #1: Voice transcription fails with Spanish audio
  - **Severity**: High
  - **Impact**: Users can't use voice notes effectively
  - **Fix**: Update Whisper language detection

### Minor Issues
_(Fill during testing)_

### UX Improvements
_(Fill during testing)_

**Example**:
- [ ] Idea #1: Show file size in document confirmations
- [ ] Idea #2: Preview thumbnails in Telegram

---

## Prompt Improvements Needed

_(Collect notes for Task 7)_

### Intent Classification
- [ ] Issue: Photo + "save this" → routes to ??? (should be NOTE)
- [ ] Fix: Update examples in classifier prompt

### Agent Prompts
- [ ] Issue: TaskAgent doesn't extract due date well
- [ ] Fix: Add more date examples

### Enrichment Questions
- [ ] Issue: Questions too formal
- [ ] Fix: Make more casual/natural

---

## Next Steps After Testing

1. **Document all issues** in this file
2. **Categorize by priority**: Critical → Minor → Nice-to-have
3. **Create Task 7 plan** based on findings
4. **Consider switching models** if qwen3:1.7b struggles (try llama3.2:3b)
5. **Update prompts** in Task 7

---

## Test Execution Log

### Session 1: Basic Functionality
**Date**: _____
**Tester**: _____
**Duration**: _____

**Results**:
- Test 1.1 (Photo): ⬜ Pass / ⬜ Fail
- Test 1.2 (Voice): ⬜ Pass / ⬜ Fail
- Test 1.3 (Document): ⬜ Pass / ⬜ Fail
- Test 1.4 (Location): ⬜ Pass / ⬜ Fail

**Notes**:
_____

### Session 2: Agent Routing
**Results**:
- LIST routing: __/4 correct
- TASK routing: __/4 correct
- NOTE routing: __/4 correct
- QUERY routing: __/4 correct

**Notes**:
_____

### Session 3: Enrichment
**Results**:
- When enrichment: ⬜ Pass / ⬜ Fail
- Who enrichment: ⬜ Pass / ⬜ Fail
- List enrichment: ⬜ Pass / ⬜ Fail

**Notes**:
_____

---

## Test Completion Checklist

- [ ] All Phase 1 tests executed
- [ ] All Phase 2 tests executed
- [ ] All Phase 3 tests executed
- [ ] All Phase 4 tests executed
- [ ] All Phase 5 tests executed
- [ ] Performance measured
- [ ] Logs reviewed
- [ ] Database verified
- [ ] Issues documented
- [ ] Prompt improvements listed
- [ ] Ready for Task 7

**Estimated Time**: 2 hours
**Actual Time**: _____
