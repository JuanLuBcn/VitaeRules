# Complete Media Experience - User Scenarios

## Scenario 1: Photo Shopping List

### User Journey
```
👤 User opens Telegram bot
👤 Takes photo of milk carton in store
👤 Sends photo with caption: "Add to shopping list"
```

### Bot Response Flow
```
🤖 VitaeBot

📷 Photo saved!

✅ Agregué 'milk carton' a la lista 📷
```

### Later That Day
```
👤 User: "What's on my shopping list?"

🤖 VitaeBot

🛒 Lista de la compra:

⬜ milk carton 📷
⬜ eggs
⬜ bread
⬜ butter 📷

4 elemento(s)
```

### Behind the Scenes
```
1. Telegram Handler
   - Downloads photo → "media/user123/photos/photo_20241026_143022_abc12345.jpg"
   - Stores with MediaHandler
   - Formats: "[Photo: media/.../photo_123.jpg] Add to shopping list"

2. Orchestrator
   - Extracts: MediaReference(type="photo", path="...", msg="Add to shopping list")
   - Routes to ListAgent with context

3. ListAgent
   - Detects: "shopping list"
   - Adds item with media_reference
   - Passes to enrichment (if needed)

4. ListTool
   - Converts media_reference → media_path
   - INSERT INTO list_items (media_path="...", metadata='{"media": {...}}')

5. Display (later query)
   - Reads media_path from database
   - Calls _get_media_indicator() → "📷"
   - Shows: "⬜ milk carton 📷"
```

---

## Scenario 2: Voice Note Task with Enrichment

### User Journey
```
👤 User holds voice button
👤 Says: "Remind me to call mom"
👤 Releases (sends voice message)
```

### Bot Response - Step 1 (Transcription)
```
🤖 VitaeBot

🎤 Transcribing your voice message...
```

### Bot Response - Step 2 (Task Created)
```
🤖 VitaeBot

🎤 Voice transcribed:
"Remind me to call mom"

✅ Perfecto, crearé la tarea: **Call mom**
```

### Bot Response - Step 3 (Enrichment Question)
```
🤖 VitaeBot

📅 ¿Cuándo quieres que te lo recuerde?

💡 Por ejemplo: "mañana a las 9", "el viernes", "en 2 horas"
```

### User Responds
```
👤 User: "Tomorrow at 9am"

🤖 VitaeBot

¡Perfecto! 📅 Mañana a las 9am

✅ Creé la tarea 'Call mom' 🎤 (📅 Tomorrow 9am)
```

### Later - Check Tasks
```
👤 User: "What are my tasks?"

🤖 VitaeBot

📋 **Tus Tareas**

Pendientes:
⬜ Call mom 🎤
   📅 Fecha: Tomorrow 9am

⬜ Finish report
   📅 Fecha: Friday

⬜ Buy groceries 📷
```

### Behind the Scenes
```
1. Telegram Handler (Voice)
   - Downloads: voice_20241026_143500_def67890.ogg
   - Whisper transcribes: "Remind me to call mom"
   - Stores voice file
   - Formats: "[Voice: media/.../voice_456.ogg] Remind me to call mom"

2. Orchestrator
   - Extracts: MediaReference(type="voice", path="...", msg="Remind me to call mom")
   - Classifies: TASK intent
   - Routes to TaskAgent with media context

3. TaskAgent
   - Extracts: title="Call mom"
   - Adds media_reference to extracted_data
   - Returns: AgentResponse(needs_enrichment=True)

4. Enrichment Flow
   - EnrichmentAgent: "When?" → User: "Tomorrow 9am"
   - Enrichment complete: final_data = {title, due_at, media_reference}

5. Orchestrator
   - Converts media_reference → media_path
   - Calls: task_tool.execute({media_path="...", due_at="..."})

6. TaskTool
   - INSERT INTO tasks (media_path="...", metadata='{"media": {"media_type": "voice"}}')

7. Display (later query)
   - Reads: media_path, metadata
   - _get_media_indicator() → "🎤"
   - Shows: "⬜ Call mom 🎤"
```

---

## Scenario 3: Document with Note

### User Journey
```
👤 User receives contract.pdf via email
👤 Forwards to Telegram bot
👤 Adds caption: "Review before Monday meeting"
```

### Bot Response
```
🤖 VitaeBot

📄 Document saved!

💾 **¿Guardar esta nota?**

**Contenido:** Review before Monday meeting
**Archivo adjunto:** 📄 contract.pdf

[User taps "Sí" or types "yes"]
```

### Bot Confirms
```
🤖 VitaeBot

💾 Nota guardada con éxito!

📄 Review before Monday meeting
```

### Later - Search Notes
```
👤 User: "What do I need to review?"

🤖 VitaeBot

🔍 Encontré esto:

📄 Review before Monday meeting (📄 contract.pdf)
Guardado: Hace 2 horas
```

### Behind the Scenes
```
1. Telegram Handler (Document)
   - Downloads: contract.pdf
   - Stores: media/user123/documents/doc_20241026_143600_ghi78901.pdf
   - Formats: "[Document: contract.pdf | media/.../doc_789.pdf] Review before Monday"

2. Orchestrator
   - Extracts: MediaReference(type="document", filename="contract.pdf", path="...", msg="Review before Monday")
   - Classifies: NOTE intent
   - Routes to NoteAgent

3. NoteAgent
   - Adds media_reference to note_data
   - Shows preview with: "📄 contract.pdf"
   - On confirm: MemoryItem(media_type="document", media_path="...")

4. MemoryService
   - Stores in vector database with media metadata
   - Indexed for retrieval

5. Query/Retrieval
   - QueryAgent searches: "review"
   - Returns notes with media info
   - Displays: "📄 Review before Monday (📄 contract.pdf)"
```

---

## Scenario 4: Location Share

### User Journey
```
👤 User at office
👤 Taps location button in Telegram
👤 Shares current location
👤 Adds message: "I'm at the office"
```

### Bot Response
```
🤖 VitaeBot

📍 Location saved!

💾 Note created: I'm at the office
📍 40.7128, -74.0060
```

### Later - Context Recall
```
👤 User: "Where was I yesterday at 2pm?"

🤖 VitaeBot

🔍 Based on your memories:

📍 You were at the office
Location: 40.7128, -74.0060
Time: Yesterday, 2:00 PM
```

### Behind the Scenes
```
1. Telegram Handler (Location)
   - Extracts: latitude=40.7128, longitude=-74.0060
   - No file storage (location is just coordinates)
   - Formats: "[Location: lat=40.7128, lon=-74.0060] I'm at the office"

2. Orchestrator
   - Extracts: MediaReference(type="location", lat=40.7128, lon=-74.0060, msg="I'm at the office")
   - Routes to NoteAgent

3. NoteAgent
   - Creates note with coordinates
   - MemoryItem(coordinates=(40.7128, -74.0060))

4. MemoryService
   - Stores with location metadata
   - Indexed by time and location

5. Retrieval
   - Can search by location radius
   - Can find "where was I when..."
```

---

## Scenario 5: Mixed Media in One List

### Building a List Over Time

#### Monday Morning
```
👤 User: "Add milk to shopping list"

🤖 ✅ Agregué 'milk' a la lista
```

#### Monday Afternoon  
```
👤 [Sends photo of eggs carton]
👤 Caption: "Add to shopping"

🤖 📷 Photo saved!
✅ Agregué 'eggs' a la lista 📷
```

#### Tuesday Morning
```
👤 [Voice note] "Add bread to shopping list"

🤖 🎤 Voice transcribed: "Add bread to shopping list"
✅ Agregué 'bread' a la lista 🎤
```

#### Tuesday Evening - Review List
```
👤 User: "Show my shopping list"

🤖 VitaeBot

🛒 Lista de la compra:

⬜ milk
⬜ eggs 📷
⬜ bread 🎤
⬜ butter
⬜ cheese 📷

5 elemento(s)
```

#### At Store - Mark Complete
```
👤 User marks items as done in app

🤖 VitaeBot

🛒 Lista de la compra:

✅ milk
✅ eggs 📷
✅ bread 🎤
⬜ butter
⬜ cheese 📷

2 items remaining
```

---

## Media Type Summary

### Visual Reference

```
📷  Photo      → Images (.jpg, .png, .jpeg)
🎤  Voice      → Audio recordings (.ogg, .mp3, .wav)
📄  Document   → Files (.pdf, .docx, .txt)
📍  Location   → GPS coordinates (no file)
📎  Generic    → Unknown type (fallback)
```

### Storage Paths

```
media/
├── user_123456/
│   ├── photos/
│   │   ├── photo_20241026_143022_abc12345.jpg
│   │   └── photo_20241026_143022_abc12345_thumb.jpg  (thumbnail)
│   │
│   ├── voice/
│   │   └── voice_20241026_143500_def67890.ogg
│   │
│   └── documents/
│       └── document_20241026_143600_ghi78901.pdf
```

### Database Storage

```sql
-- Tasks
INSERT INTO tasks (
    id, title, media_path, metadata
) VALUES (
    'task_123',
    'Call mom',
    'media/user123/voice/voice_456.ogg',
    '{"media": {"media_type": "voice", "media_path": "..."}}'
);

-- List Items
INSERT INTO list_items (
    id, text, media_path, metadata
) VALUES (
    'item_456',
    'Eggs',
    'media/user123/photos/photo_789.jpg',
    '{"media": {"media_type": "photo", "media_path": "..."}}'
);

-- Memory Items
INSERT INTO memory_items (
    id, content, media_type, media_path, coordinates
) VALUES (
    'mem_789',
    'At the office',
    'location',
    NULL,
    '(40.7128, -74.0060)'
);
```

---

## User Benefits

### Visual Feedback
- **Immediate recognition**: See media type at a glance
- **No text clutter**: Single emoji, not long descriptions
- **Consistent**: Same emoji system everywhere

### Memory Triggers
- **Photo reminder**: "Oh right, that milk carton looked expired"
- **Voice context**: "I remember the exact words I said"
- **Document reference**: "That was the important contract"

### Organization
- **Filter mentally**: "Which tasks have voice notes?"
- **Prioritize**: "Items with photos are urgent (I took a picture for a reason)"
- **Track**: "How many items have attachments?"

### Confidence
- **Verification**: Media emoji confirms attachment was saved
- **Retrieval**: Know you can access the original file later
- **Completeness**: All information preserved, not just text

---

## Complete Feature Matrix

| Feature | Status | Display |
|---------|--------|---------|
| Photo upload | ✅ | 📷 |
| Voice transcription | ✅ | 🎤 |
| Document storage | ✅ | 📄 |
| Location sharing | ✅ | 📍 |
| Media in tasks | ✅ | Task list shows emoji |
| Media in lists | ✅ | List items show emoji |
| Media in notes | ✅ | Note display shows emoji |
| Success messages | ✅ | Confirmation shows emoji |
| Enrichment flow | ✅ | Media preserved through questions |
| Database storage | ✅ | media_path + metadata fields |
| Retrieval | ✅ | Media info in search results |

**100% Complete!** 🎉

All media types supported end-to-end with visual indicators throughout the user experience.
