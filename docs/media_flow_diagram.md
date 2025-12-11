# Phase 3 Media Support - Complete Data Flow

## End-to-End Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ TELEGRAM USER INTERACTION                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  User sends:  📷 Photo + "My new car"                                      │
│               🎤 Voice note saying "Remind me to call mom"                 │
│               📄 contract.pdf + "Review this"                              │
│               📍 Location (40.7128, -74.0060)                              │
│                                                                             │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ TELEGRAM ADAPTER (src/app/adapters/telegram.py)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  handle_photo()      → Downloads file to temp                              │
│  handle_voice()      → Transcribes with Whisper                            │
│  handle_document()   → Downloads with original name                        │
│  handle_location()   → Extracts coordinates                                │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────┐             │
│  │ MediaHandler.store_{type}()                               │             │
│  │   ✓ Validates file size (10MB/20MB/50MB)                  │             │
│  │   ✓ Creates unique filename (timestamp + UUID)            │             │
│  │   ✓ Stores in user-specific directory                     │             │
│  │   ✓ Generates thumbnail (photos only)                     │             │
│  │   ✓ Returns: {"media_path": "media/user123/photos/..."}   │             │
│  └───────────────────────────────────────────────────────────┘             │
│                                                                             │
│  Formats message:                                                           │
│    "[Photo: media/user123/photos/photo_20241026_123456_abc12345.jpg] My car"│
│    "[Voice: media/user123/voice/voice_20241026_123500_def67890.ogg] Rem..." │
│    "[Document: contract.pdf | media/user123/documents/doc_...pdf] Review"  │
│    "[Location: lat=40.7128, lon=-74.0060] I'm sharing my location"         │
│                                                                             │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ORCHESTRATOR (src/app/agents/orchestrator.py)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  handle_message(message, chat_id, user_id)                                 │
│                                                                             │
│  Step 1: Extract Media Reference                                           │
│  ┌──────────────────────────────────────────────────────────────┐          │
│  │ extract_media_reference(message)                             │          │
│  │   Returns: (clean_message, MediaReference)                   │          │
│  │                                                               │          │
│  │   MediaReference:                                             │          │
│  │     • media_type: "photo" | "voice" | "document" | "location"│          │
│  │     • clean_message: "My new car" (prefix removed)            │          │
│  │     • media_path: "media/user123/photos/..."                 │          │
│  │     • latitude/longitude: (for location)                      │          │
│  │     • filename: "contract.pdf" (for documents)                │          │
│  └──────────────────────────────────────────────────────────────┘          │
│                                                                             │
│  Step 2: Classify Intent (using clean_message)                             │
│    "My new car" → NOTE intent                                               │
│    "Remind me to call mom" → TASK intent                                    │
│                                                                             │
│  Step 3: Route to Agent with Media Context                                 │
│    context = {"media_reference": MediaReference(...)}                       │
│    agent.handle(clean_message, chat_id, user_id, context)                  │
│                                                                             │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            │                                     │
            ▼                                     ▼
┌─────────────────────────────────┐  ┌──────────────────────────────────┐
│ NOTE AGENT                      │  │ TASK AGENT                       │
│ (src/app/agents/note_agent.py) │  │ (src/app/agents/task_agent.py)   │
├─────────────────────────────────┤  ├──────────────────────────────────┤
│                                 │  │                                  │
│ handle(msg, chat_id, uid, ctx)  │  │ handle(msg, chat_id, uid, ctx)   │
│                                 │  │                                  │
│ 1. Extract note details         │  │ 1. Store context internally      │
│ 2. Get media from context:      │  │ 2. Detect operation type         │
│    if "media_reference" in ctx: │  │ 3. For create operation:         │
│      note_data["media_ref"] = .. │  │    extracted_data["media_ref"] =│
│                                 │  │      ctx["media_reference"]      │
│ 3. Preview with media:          │  │                                  │
│    "💾 Save note?               │  │ Returns AgentResponse:           │
│     Content: My new car         │  │   needs_enrichment=True          │
│     📷 Photo"                   │  │   extracted_data={...}           │
│                                 │  │                                  │
│ 4. On confirm:                  │  │                                  │
│    MemoryItem(                  │  │                                  │
│      media_type="photo",        │  │                                  │
│      media_path="...",          │  │                                  │
│      metadata={"media": {...}}  │  │                                  │
│    )                            │  │                                  │
│                                 │  │                                  │
└─────────────────────────────────┘  └──────────┬───────────────────────┘
                                                 │
                                                 ▼
                      ┌─────────────────────────────────────────────────────┐
                      │ ENRICHMENT AGENT (src/app/agents/enrichment_agent.py)│
                      ├─────────────────────────────────────────────────────┤
                      │                                                     │
                      │ Multi-turn conversation to gather missing context: │
                      │                                                     │
                      │ Bot:  "📅 ¿Cuándo quieres que te lo recuerde?"     │
                      │ User: "Tomorrow at 9am"                            │
                      │ Bot:  "👥 ¿Con quién?"                              │
                      │ User: "Skip"                                        │
                      │                                                     │
                      │ Final data includes:                                │
                      │   • original extracted_data                         │
                      │   • gathered enrichment (due_at, people, etc.)      │
                      │   • media_reference (passed through unchanged)      │
                      │                                                     │
                      │ Returns AgentResponse:                              │
                      │   needs_enrichment=False                            │
                      │   extracted_data={title, due_at, media_reference}  │
                      │                                                     │
                      └──────────────────────┬──────────────────────────────┘
                                            │
                                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ORCHESTRATOR - Tool Execution                                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  _execute_tool_operation(agent_response, intent, chat_id, user_id)         │
│                                                                             │
│  1. Get tool (list_tool or task_tool)                                      │
│                                                                             │
│  2. Prepare tool data:                                                     │
│     tool_data = dict(agent_response.extracted_data)                        │
│                                                                             │
│  3. Convert media_reference → tool fields:                                 │
│     ┌────────────────────────────────────────────────────────┐             │
│     │ if "media_reference" in tool_data:                     │             │
│     │   media_ref = tool_data.pop("media_reference")         │             │
│     │   if media_ref.media_path:                             │             │
│     │     tool_data["media_path"] = media_ref.media_path     │             │
│     │   if media_ref.latitude is not None:                   │             │
│     │     tool_data["latitude"] = media_ref.latitude         │             │
│     │     tool_data["longitude"] = media_ref.longitude       │             │
│     └────────────────────────────────────────────────────────┘             │
│                                                                             │
│  4. Execute tool:                                                           │
│     await tool.execute(tool_data)                                           │
│                                                                             │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            │                                     │
            ▼                                     ▼
┌─────────────────────────────────┐  ┌──────────────────────────────────┐
│ TASK TOOL                       │  │ MEMORY SERVICE                   │
│ (src/app/tools/task_tool.py)   │  │ (src/app/memory/service.py)      │
├─────────────────────────────────┤  ├──────────────────────────────────┤
│                                 │  │                                  │
│ execute(arguments)              │  │ add_item(memory_item)            │
│                                 │  │                                  │
│ _create_task(args):             │  │ Stores MemoryItem with:          │
│   • Extract fields              │  │   • media_type: "photo"          │
│   • media_path = args.get(...)  │  │   • media_path: "media/..."      │
│   • latitude = args.get(...)    │  │   • coordinates: (lat, lon)      │
│   • longitude = args.get(...)   │  │   • metadata: {"media": {...}}   │
│                                 │  │                                  │
│ INSERT INTO tasks:              │  │ INSERT INTO memories:            │
│   (id, title, description,      │  │   (id, title, content,           │
│    media_path, latitude,        │  │    media_type, media_path,       │
│    longitude, metadata, ...)    │  │    coordinates, metadata, ...)   │
│                                 │  │                                  │
└─────────────────────────────────┘  └──────────────────────────────────┘
```

## Key Components

### 1. MediaReference (Data Structure)
```python
@dataclass
class MediaReference:
    media_type: str              # photo, voice, document, location
    clean_message: str           # Message with prefix removed  
    media_path: Optional[str]    # Path to stored file
    latitude: Optional[float]    # GPS latitude
    longitude: Optional[float]   # GPS longitude
    filename: Optional[str]      # Original filename

    def to_dict() -> dict        # Serialize for storage
```

### 2. Message Format Patterns

| Media Type | Format                                    | Example |
|------------|-------------------------------------------|---------|
| Photo      | `[Photo: path] caption`                   | `[Photo: media/user123/photos/photo_123.jpg] My new car` |
| Voice      | `[Voice: path] transcription`             | `[Voice: media/user123/voice/voice_456.ogg] Remind me to call mom` |
| Document   | `[Document: filename \| path] description`| `[Document: contract.pdf \| media/user123/documents/doc_789.pdf] Review` |
| Location   | `[Location: lat=X, lon=Y] context`        | `[Location: lat=40.7128, lon=-74.0060] I'm at the office` |

### 3. Context Passing

```python
# Orchestrator → Agent
agent.handle(message, chat_id, user_id, context={"media_reference": media_ref})

# Agent → Enrichment (via extracted_data)
AgentResponse(extracted_data={"media_reference": media_ref, ...})

# Enrichment → Tool (via orchestrator conversion)
tool.execute({"media_path": "...", "latitude": 40.7128, "longitude": -74.0060})
```

### 4. Database Fields

**Tasks Table**:
```sql
media_path TEXT,
latitude REAL,
longitude REAL,
metadata JSON  -- {"media": {"media_type": "voice", "media_path": "..."}}
```

**Memories Table** (MemoryItem):
```python
media_type: str | None
media_path: str | None
coordinates: tuple[float, float] | None
metadata: dict  -- {"media": {...}}
```

## Flow Examples

### Example 1: Photo → Note
```
1. User sends photo "My new car"
2. Telegram: handle_photo() → store → format message
3. Orchestrator: extract media → route to NoteAgent
4. NoteAgent: add media to note_data → show preview with 📷
5. User: confirms
6. NoteAgent: execute_confirmed() → MemoryItem(media_path="...")
7. MemoryService: INSERT with media fields
8. Response: "💾 Note saved (📷 Photo)"
```

### Example 2: Voice → Task → Enrichment
```
1. User sends voice "Remind me to call mom"
2. Telegram: handle_voice() → transcribe → store → format
3. Orchestrator: extract media → route to TaskAgent
4. TaskAgent: create task with media_reference
5. EnrichmentAgent: "📅 When?" → User: "Tomorrow 9am"
6. EnrichmentAgent: complete → final_data with media_reference
7. Orchestrator: convert media_reference → media_path
8. TaskTool: INSERT task(media_path="...", due_at="tomorrow 9am")
9. Response: "✅ Task created: Call mom (🎤 Voice note)"
```

### Example 3: Location → Note
```
1. User shares location (40.7128, -74.0060)
2. Telegram: handle_location() → format message
3. Orchestrator: extract media (lat/lon) → route to NoteAgent
4. NoteAgent: create note with coordinates
5. MemoryService: INSERT with coordinates=(40.7128, -74.0060)
6. Response: "💾 Location saved (📍 40.7128, -74.006)"
```

## Success Criteria

✅ **Media flows through complete pipeline**  
✅ **Clean separation of concerns** (media extraction → agents work with clean text)  
✅ **Type safety** (MediaReference provides structure)  
✅ **User-friendly** (emoji indicators, clean previews)  
✅ **Extensible** (easy to add new media types)  
✅ **Database ready** (all fields stored correctly)  
✅ **Backward compatible** (works with existing code)

## Next Step (Task 5)

Update **display** in ListTool and TaskTool:
- Show media indicators when listing items
- Format: "🛒 Milk (📷 Photo)"
- Format: "✅ Call mom (🎤 Voice note)"
