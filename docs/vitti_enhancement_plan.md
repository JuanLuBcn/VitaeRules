# Vitti Enhancement Plan - Enrichment & Media

## 📋 Decisions Made

### 1. Enrichment Strategy
**Option C + A: Smart detection with multi-turn conversation**
- Vitti intelligently detects which fields make sense to ask about
- One question at a time for natural conversation flow
- User can skip with "ya" / "guardar" / "listo"

### 2. Media Storage
**Original files** - No compression
- Preserve quality
- User owns their data
- Storage is cheap, quality is valuable

### 3. Voice Notes
**Auto-transcribe** using Whisper API
- Transcription becomes input for Vitti
- Store both audio file + transcription text
- Searchable by transcribed content
- User message = transcription

### 4. Location Privacy
**Exact coordinates**
- Store precise lat/long
- User chooses what to share
- Useful for specific place memories

### 5. Google Maps API
**Free Tier**
- Geocoding API (coordinates ↔ address)
- Places API Basic
- 28,000 requests/month free
- More than enough for personal use

### 6. Branding
**"Vitti"** throughout the app
- Update all prompts
- Update all documentation
- Conversational personality

---

## 🗃️ Database Schema Updates

### ListTool Schema Enhancement

**Current tables:**
```sql
CREATE TABLE lists (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    user_id TEXT,
    chat_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)

CREATE TABLE list_items (
    id TEXT PRIMARY KEY,
    list_id TEXT NOT NULL,
    text TEXT NOT NULL,
    completed INTEGER DEFAULT 0,
    position INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT
)
```

**NEW: Add to list_items:**
```sql
ALTER TABLE list_items ADD COLUMN people TEXT;          -- JSON array: ["Juan", "María"]
ALTER TABLE list_items ADD COLUMN location TEXT;        -- "Mercadona, Calle Mayor"
ALTER TABLE list_items ADD COLUMN latitude REAL;        -- 40.416775
ALTER TABLE list_items ADD COLUMN longitude REAL;       -- -3.703790
ALTER TABLE list_items ADD COLUMN place_id TEXT;        -- Google Place ID
ALTER TABLE list_items ADD COLUMN tags TEXT;            -- JSON array: ["urgente", "orgánico"]
ALTER TABLE list_items ADD COLUMN notes TEXT;           -- Additional notes
ALTER TABLE list_items ADD COLUMN media_path TEXT;      -- Photo of item
ALTER TABLE list_items ADD COLUMN metadata TEXT;        -- JSON for extensions
```

**Use cases:**
- "Comprar vino para la cena con Juan" → people: ["Juan"]
- "Recoger paquete en Correos de Gran Vía" → location: "Correos, Gran Vía"
- Share location when adding item → coordinates + place_id
- Photo of product → media_path

---

### TaskTool Schema Enhancement

**Current table:**
```sql
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    due_at TEXT,
    priority INTEGER DEFAULT 0,
    completed INTEGER DEFAULT 0,
    user_id TEXT,
    chat_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT
)
```

**NEW: Add to tasks:**
```sql
ALTER TABLE tasks ADD COLUMN people TEXT;              -- JSON array: ["Juan", "María"]
ALTER TABLE tasks ADD COLUMN location TEXT;            -- "Oficina principal"
ALTER TABLE tasks ADD COLUMN latitude REAL;            -- 40.416775
ALTER TABLE tasks ADD COLUMN longitude REAL;           -- -3.703790
ALTER TABLE tasks ADD COLUMN place_id TEXT;            -- Google Place ID
ALTER TABLE tasks ADD COLUMN tags TEXT;                -- JSON array: ["trabajo", "urgente"]
ALTER TABLE tasks ADD COLUMN media_path TEXT;          -- Attachment/reference
ALTER TABLE tasks ADD COLUMN metadata TEXT;            -- JSON for extensions
ALTER TABLE tasks ADD COLUMN reminder_distance INTEGER; -- Meters for location-based reminder
```

**Use cases:**
- "Llamar a Juan sobre el proyecto" → people: ["Juan"]
- "Reunión en la oficina de Madrid" → location + coordinates
- "Comprar en Mercadona" → location-based reminder
- Task with reference photo → media_path

---

## 🎯 Implementation Phases

### Phase 1: Database Migration & Enhanced Tools ✅ READY TO CODE
**Files to modify:**
- `src/app/tools/list_tool.py` - Add new fields
- `src/app/tools/task_tool.py` - Add new fields
- Add migration script for existing databases

**Tasks:**
1. Create migration script
2. Update ListTool schema and operations
3. Update TaskTool schema and operations
4. Update tool field documentation
5. Test with enhanced data

---

### Phase 2: Smart Enrichment Agent 🎯 NEXT
**New files to create:**
- `src/app/agents/enrichment_agent.py` - Smart follow-up questions
- `src/app/agents/enrichment_rules.py` - Context detection rules

**Logic:**
```python
class EnrichmentAgent:
    async def should_enrich(self, agent_type, data):
        """Decide if enrichment is needed."""
        
        # For memories about people
        if data.people and not data.location:
            return "location_for_event"
        
        # For tasks without due date
        if agent_type == "task" and not data.due_at:
            return "ask_due_date"
        
        # For anything without tags
        if not data.tags:
            return "suggest_tags"
    
    async def ask_enrichment(self, enrichment_type, current_data):
        """Generate smart follow-up question."""
        
        if enrichment_type == "location_for_event":
            return "¿Dónde fue esto? Puedes compartir una ubicación 📍 o escribir el lugar."
        
        if enrichment_type == "ask_due_date":
            return "¿Para cuándo es esta tarea? (ej: mañana, viernes, en 2 días)"
```

---

### Phase 3: Media Handler 📸🎙️
**New files to create:**
- `src/app/media/handler.py` - Process photos, audio, locations
- `src/app/media/storage.py` - File storage management
- `src/app/media/transcription.py` - Whisper API integration

**Media workflow:**
```python
class MediaHandler:
    async def process_photo(self, telegram_file):
        """
        1. Download from Telegram
        2. Save to storage/{user_id}/photos/{file_id}.jpg
        3. Extract metadata (size, dimensions)
        4. Return media_path for database
        """
    
    async def process_voice(self, telegram_file):
        """
        1. Download from Telegram
        2. Save to storage/{user_id}/audio/{file_id}.ogg
        3. Transcribe with Whisper API
        4. Return: (audio_path, transcription_text)
        5. Transcription becomes user input for Vitti
        """
    
    async def process_location(self, lat, lon):
        """
        1. Reverse geocode with Google
        2. Get formatted address
        3. Get Place ID if available
        4. Return: (location_string, place_id, metadata)
        """
```

---

### Phase 4: Google Maps Integration 🗺️
**Setup:**
1. Google Cloud Console setup (Free Tier)
2. Enable APIs:
   - Geocoding API
   - Places API (Basic)
   - Static Maps API (optional - for images)

**New files:**
- `src/app/integrations/google_maps.py`

**Configuration:**
```python
# .env
GOOGLE_MAPS_API_KEY=your_key_here
GOOGLE_MAPS_ENABLED=true
```

**Features:**
```python
class GoogleMapsService:
    async def reverse_geocode(self, lat, lon):
        """Coordinates → Address"""
        
    async def geocode(self, address):
        """Address → Coordinates"""
        
    async def get_place_details(self, place_id):
        """Get rich info about a place"""
        
    async def search_places(self, query, location):
        """Find nearby places"""
```

---

### Phase 5: Update Agents for Enrichment 🤖

**Modify existing agents:**
- `ListAgent` - Ask about people/location for items
- `TaskAgent` - Ask about due_at, priority, location
- `NoteAgent` - Already good, add media prompts
- `QueryAgent` - Search by new fields

**Integration with orchestrator:**
```python
class AgentOrchestrator:
    async def handle_message(self, message, chat_id, user_id):
        # ... existing routing ...
        
        result = await agent.handle(message, chat_id, user_id)
        
        # NEW: Check if enrichment needed
        if result.needs_enrichment:
            enrichment_question = await self.enrichment_agent.ask(
                agent_type=agent.name,
                current_data=result.data
            )
            
            self.pending_enrichments[chat_id] = {
                "agent": agent,
                "data": result.data,
                "enrichment_state": "awaiting_response"
            }
            
            return {
                "message": f"{result.message}\n\n{enrichment_question}",
                "needs_enrichment": True
            }
```

---

### Phase 6: Telegram Adapter Updates 📱

**Handle new message types:**
```python
async def handle_message(self, update, context):
    # Existing text handling
    if update.message.text:
        # ... existing logic ...
    
    # NEW: Photo handling
    elif update.message.photo:
        photo = update.message.photo[-1]  # Largest size
        caption = update.message.caption or ""
        
        media_path = await self.media_handler.process_photo(photo)
        
        # Ask Vitti what to do with photo
        result = await self.orchestrator.handle_media(
            media_type="photo",
            media_path=media_path,
            caption=caption,
            chat_id=chat_id,
            user_id=user_id
        )
    
    # NEW: Voice handling
    elif update.message.voice:
        voice = update.message.voice
        
        audio_path, transcription = await self.media_handler.process_voice(voice)
        
        # Transcription becomes input
        result = await self.orchestrator.handle_message(
            message=transcription,
            chat_id=chat_id,
            user_id=user_id,
            metadata={"audio_path": audio_path, "is_transcription": True}
        )
    
    # NEW: Location handling
    elif update.message.location:
        location = update.message.location
        
        location_data = await self.media_handler.process_location(
            location.latitude,
            location.longitude
        )
        
        result = await self.orchestrator.handle_location(
            location_data=location_data,
            chat_id=chat_id,
            user_id=user_id
        )
```

---

## 🎨 User Experience Flows

### Flow 1: Adding Item with Location
```
User: "Comprar queso feta en Mercadona"
Vitti: "🛒 ¿Añadir queso feta a tu lista de la compra?"
User: "sí"
Vitti: "¿En qué Mercadona? Puedes compartir la ubicación 📍"
User: [shares location]
Vitti: "✅ Añadido: queso feta
       📍 Mercadona, Calle Gran Vía 45, Madrid"
```

### Flow 2: Task with People and Due Date
```
User: "Llamar a Juan sobre el proyecto"
Vitti: "📋 ¿Crear esta tarea?
       Tarea: Llamar a Juan sobre el proyecto
       Personas: Juan"
User: "sí"
Vitti: "¿Para cuándo? (ej: mañana, viernes)"
User: "mañana por la tarde"
Vitti: "¿Qué prioridad? 
       1️⃣ Baja  2️⃣ Media  3️⃣ Alta  4️⃣ Urgente"
User: "2"
Vitti: "✅ Tarea creada: Llamar a Juan sobre el proyecto
       📅 Fecha: 27 Oct 2025, 17:00
       ⭐ Prioridad: Media"
```

### Flow 3: Voice Note Memory
```
User: [sends voice note: "Hoy estuve con María en el café y me contó sobre su nuevo trabajo..."]
[Auto-transcription happens]
Vitti: "💾 Voy a guardar esta nota.
       
       Contenido: Hoy estuve con María en el café y me contó sobre su nuevo trabajo...
       🎙️ Audio guardado
       Personas: María
       
       ¿En qué café fue? (puedes compartir ubicación 📍)"
User: [shares location]
Vitti: "✅ Nota guardada con audio
       📍 Café Central, Plaza Mayor"
```

### Flow 4: Photo with Task
```
User: [sends photo of broken pipe with caption "Arreglar esto"]
Vitti: "¿Qué quieres hacer con esta foto?
       1️⃣ Crear tarea
       2️⃣ Guardar como nota
       3️⃣ Añadir a lista"
User: "1"
Vitti: "📋 ¿Crear tarea: Arreglar esto?
       📸 Foto adjunta"
User: "sí"
Vitti: "¿Para cuándo es esto?"
User: "urgente, esta semana"
Vitti: "✅ Tarea creada: Arreglar esto
       📸 Con foto de referencia
       📅 Esta semana
       ⭐ Prioridad: Alta"
```

---

## 📊 Database Migration Script

```python
# scripts/migrate_enhanced_fields.py
"""
Migration: Add people, location, media fields to lists and tasks
Version: 2.0
Date: 2025-10-26
"""

import sqlite3
from pathlib import Path

def migrate_lists_db(db_path: Path):
    """Add enhanced fields to list_items table."""
    with sqlite3.connect(db_path) as conn:
        # Check if migration needed
        cursor = conn.execute("PRAGMA table_info(list_items)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "people" not in columns:
            print("Migrating list_items table...")
            
            conn.execute("ALTER TABLE list_items ADD COLUMN people TEXT")
            conn.execute("ALTER TABLE list_items ADD COLUMN location TEXT")
            conn.execute("ALTER TABLE list_items ADD COLUMN latitude REAL")
            conn.execute("ALTER TABLE list_items ADD COLUMN longitude REAL")
            conn.execute("ALTER TABLE list_items ADD COLUMN place_id TEXT")
            conn.execute("ALTER TABLE list_items ADD COLUMN tags TEXT")
            conn.execute("ALTER TABLE list_items ADD COLUMN notes TEXT")
            conn.execute("ALTER TABLE list_items ADD COLUMN media_path TEXT")
            conn.execute("ALTER TABLE list_items ADD COLUMN metadata TEXT")
            
            conn.commit()
            print("✅ list_items migration complete")

def migrate_tasks_db(db_path: Path):
    """Add enhanced fields to tasks table."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("PRAGMA table_info(tasks)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if "people" not in columns:
            print("Migrating tasks table...")
            
            conn.execute("ALTER TABLE tasks ADD COLUMN people TEXT")
            conn.execute("ALTER TABLE tasks ADD COLUMN location TEXT")
            conn.execute("ALTER TABLE tasks ADD COLUMN latitude REAL")
            conn.execute("ALTER TABLE tasks ADD COLUMN longitude REAL")
            conn.execute("ALTER TABLE tasks ADD COLUMN place_id TEXT")
            conn.execute("ALTER TABLE tasks ADD COLUMN tags TEXT")
            conn.execute("ALTER TABLE tasks ADD COLUMN media_path TEXT")
            conn.execute("ALTER TABLE tasks ADD COLUMN reminder_distance INTEGER")
            conn.execute("ALTER TABLE tasks ADD COLUMN metadata TEXT")
            
            conn.commit()
            print("✅ tasks migration complete")

if __name__ == "__main__":
    from app.config import get_settings
    settings = get_settings()
    
    lists_db = settings.storage_path / "lists.sqlite"
    tasks_db = settings.storage_path / "tasks.sqlite"
    
    if lists_db.exists():
        migrate_lists_db(lists_db)
    
    if tasks_db.exists():
        migrate_tasks_db(tasks_db)
    
    print("\n✅ All migrations complete!")
```

---

## ✅ Ready to Start!

I'm ready to implement this in phases. Shall we start with **Phase 1: Database Migration & Enhanced Tools**?

This includes:
1. Create migration script
2. Update ListTool with new fields
3. Update TaskTool with new fields
4. Update agents to use new fields
5. Test everything

After Phase 1 is solid, we move to Phase 2 (Smart Enrichment), then Phase 3 (Media), etc.

Should I start coding Phase 1? 🚀
