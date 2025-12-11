# Phase 3: Media, Testing & Production - Implementation Plan

**Date:** October 26, 2025  
**Scope:** Media Support + Manual Testing + Production Readiness  
**Estimated Time:** 10-12 hours  
**Goal:** Production-ready bot with rich media support

---

## 🎯 Overview

**What We're Building:**
1. **Media Support** - Photos, voice notes, document attachments
2. **Voice Transcription** - Automatic Whisper integration
3. **Manual Testing** - Real LLM validation and refinement
4. **Production Readiness** - Monitoring, error handling, deployment

**Why This Combination:**
- ✅ Telegram already supports media/voice naturally
- ✅ Completes the enrichment story (text + media)
- ✅ Testing ensures quality before production
- ✅ Production deployment gets real user feedback
- ✅ No external API dependencies (Whisper can be local)
- ✅ CrewAI migration can happen in parallel later

---

## 📋 Phase 3 TODO List

### Part A: Media Handler Foundation (3 hours)

- [ ] **A1: Media Storage Service** (1.5h)
  - Create `src/app/services/media_handler.py`
  - File storage (local with configurable path)
  - Unique filename generation (UUID-based)
  - File type validation (images, audio, documents)
  - Size limits and cleanup policies
  - Thumbnail generation for images (optional)

- [ ] **A2: Whisper Integration** (1h)
  - Create `src/app/integrations/whisper_service.py`
  - Support both local Whisper and API
  - Audio format conversion (ogg → wav)
  - Bilingual transcription (Spanish/English)
  - Fallback handling if Whisper unavailable

- [ ] **A3: Telegram Media Handlers** (30min)
  - Update `src/app/telegram/handlers.py`
  - Handle photo messages
  - Handle voice messages
  - Handle document attachments
  - Handle location shares (store as location field)

### Part B: Enrichment Integration (2 hours)

- [ ] **B1: Media in Enrichment Flow** (1h)
  - Update `EnrichmentAgent` to accept media metadata
  - Store `media_path` in enriched_data
  - Display media info in responses ("📸 Photo attached")
  - Handle media during tool execution

- [ ] **B2: Tool Updates** (1h)
  - Update `ListTool.add_item()` to handle media_path
  - Update `TaskTool.create_task()` to handle media_path
  - Update query operations to return media info
  - Add media preview in results

### Part C: Manual Testing & Refinement (3 hours)

- [ ] **C1: Real LLM Testing** (1.5h)
  - Test enrichment with Ollama/OpenAI
  - Test all conversation flows (skip, cancel, complete)
  - Test media upload workflows
  - Test voice note transcription
  - Document edge cases and failures

- [ ] **C2: Prompt Refinement** (1h)
  - Improve enrichment questions based on testing
  - Better error messages
  - Add examples in prompts
  - Tune field detection rules
  - Optimize response formatting

- [ ] **C3: Performance Optimization** (30min)
  - Measure enrichment latency
  - Cache common extractions
  - Reduce unnecessary LLM calls
  - Parallel field detection if possible

### Part D: Production Readiness (2-3 hours)

- [ ] **D1: Monitoring & Metrics** (1h)
  - Create `src/app/monitoring/enrichment_metrics.py`
  - Track enrichment usage (started, completed, skipped, cancelled)
  - Track media uploads (count, types, sizes)
  - Track conversation lengths
  - Export metrics for analysis

- [ ] **D2: Error Handling** (1h)
  - Comprehensive error recovery in all flows
  - User-friendly error messages
  - Fallback behaviors (e.g., if Whisper fails)
  - Graceful degradation
  - Error logging with context

- [ ] **D3: Documentation & Deployment** (1-2h)
  - Update all documentation
  - Create deployment guide
  - Environment variable checklist
  - Configuration examples
  - User manual with examples
  - Prepare production deployment

---

## 🗂️ Detailed Implementation

### A1: Media Storage Service

**File:** `src/app/services/media_handler.py`

```python
"""Media file storage and management."""

import os
import shutil
from pathlib import Path
from datetime import datetime
from uuid import uuid4
from typing import Optional
from PIL import Image

from app.config import get_settings
from app.tracing import get_tracer

logger = get_tracer()


class MediaHandler:
    """Handle media file storage and retrieval."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize media handler."""
        self.settings = get_settings()
        self.storage_path = storage_path or self.settings.media_storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Size limits (configurable)
        self.max_image_size_mb = 10
        self.max_audio_size_mb = 20
        self.max_document_size_mb = 50
        
        logger.info(f"MediaHandler initialized at {self.storage_path}")
    
    async def store_photo(self, file_path: Path, user_id: str) -> dict:
        """
        Store a photo file.
        
        Args:
            file_path: Temporary file path from Telegram
            user_id: User identifier
        
        Returns:
            dict with media_path, thumbnail_path, size, etc.
        """
        # Generate unique filename
        file_ext = file_path.suffix
        unique_name = f"{datetime.now().strftime('%Y%m%d')}_{uuid4().hex[:8]}{file_ext}"
        
        # User-specific directory
        user_dir = self.storage_path / user_id / "photos"
        user_dir.mkdir(parents=True, exist_ok=True)
        
        final_path = user_dir / unique_name
        
        # Copy file
        shutil.copy2(file_path, final_path)
        
        # Get file info
        file_size = final_path.stat().st_size
        
        # Generate thumbnail (optional)
        thumbnail_path = None
        try:
            thumbnail_path = await self._create_thumbnail(final_path)
        except Exception as e:
            logger.warning(f"Could not create thumbnail: {e}")
        
        logger.info(f"Stored photo: {final_path} ({file_size} bytes)")
        
        return {
            "media_path": str(final_path.relative_to(self.storage_path)),
            "thumbnail_path": str(thumbnail_path.relative_to(self.storage_path)) if thumbnail_path else None,
            "file_size": file_size,
            "media_type": "photo",
            "original_name": file_path.name,
        }
    
    async def store_voice(self, file_path: Path, user_id: str) -> dict:
        """Store a voice note file."""
        file_ext = file_path.suffix or ".ogg"
        unique_name = f"{datetime.now().strftime('%Y%m%d')}_{uuid4().hex[:8]}{file_ext}"
        
        user_dir = self.storage_path / user_id / "voice"
        user_dir.mkdir(parents=True, exist_ok=True)
        
        final_path = user_dir / unique_name
        shutil.copy2(file_path, final_path)
        
        file_size = final_path.stat().st_size
        
        logger.info(f"Stored voice note: {final_path} ({file_size} bytes)")
        
        return {
            "media_path": str(final_path.relative_to(self.storage_path)),
            "file_size": file_size,
            "media_type": "voice",
            "original_name": file_path.name,
        }
    
    async def store_document(self, file_path: Path, user_id: str) -> dict:
        """Store a document file."""
        file_ext = file_path.suffix
        unique_name = f"{datetime.now().strftime('%Y%m%d')}_{uuid4().hex[:8]}{file_ext}"
        
        user_dir = self.storage_path / user_id / "documents"
        user_dir.mkdir(parents=True, exist_ok=True)
        
        final_path = user_dir / unique_name
        shutil.copy2(file_path, final_path)
        
        file_size = final_path.stat().st_size
        
        logger.info(f"Stored document: {final_path} ({file_size} bytes)")
        
        return {
            "media_path": str(final_path.relative_to(self.storage_path)),
            "file_size": file_size,
            "media_type": "document",
            "original_name": file_path.name,
        }
    
    async def get_media(self, media_path: str) -> Optional[Path]:
        """Retrieve media file by path."""
        full_path = self.storage_path / media_path
        
        if full_path.exists():
            return full_path
        
        logger.warning(f"Media not found: {media_path}")
        return None
    
    async def delete_media(self, media_path: str) -> bool:
        """Delete a media file."""
        full_path = self.storage_path / media_path
        
        if full_path.exists():
            full_path.unlink()
            logger.info(f"Deleted media: {media_path}")
            return True
        
        return False
    
    async def _create_thumbnail(self, image_path: Path, max_size: tuple = (200, 200)) -> Path:
        """Create a thumbnail for an image."""
        thumbnail_dir = image_path.parent / "thumbnails"
        thumbnail_dir.mkdir(exist_ok=True)
        
        thumbnail_path = thumbnail_dir / f"thumb_{image_path.name}"
        
        with Image.open(image_path) as img:
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            img.save(thumbnail_path, optimize=True)
        
        return thumbnail_path
    
    async def cleanup_old_media(self, days: int = 90) -> int:
        """Delete media files older than specified days."""
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        deleted_count = 0
        
        for media_file in self.storage_path.rglob("*"):
            if media_file.is_file():
                if media_file.stat().st_mtime < cutoff:
                    media_file.unlink()
                    deleted_count += 1
        
        logger.info(f"Cleaned up {deleted_count} old media files")
        return deleted_count
```

**Tests:** `tests/unit/test_media_handler.py`

---

### A2: Whisper Integration

**File:** `src/app/integrations/whisper_service.py`

```python
"""Whisper speech-to-text integration."""

import os
from pathlib import Path
from typing import Optional

from app.config import get_settings
from app.tracing import get_tracer

logger = get_tracer()

# Try to import whisper (optional dependency)
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("Whisper not available. Install with: pip install openai-whisper")


class WhisperService:
    """Transcribe audio using Whisper."""
    
    def __init__(self, model_name: str = "base"):
        """
        Initialize Whisper service.
        
        Args:
            model_name: Whisper model (tiny, base, small, medium, large)
        """
        self.settings = get_settings()
        self.model_name = model_name
        self.model = None
        
        if WHISPER_AVAILABLE:
            logger.info(f"Loading Whisper model: {model_name}...")
            self.model = whisper.load_model(model_name)
            logger.info("Whisper model loaded")
        else:
            logger.warning("Whisper not available")
    
    async def transcribe(
        self, 
        audio_path: Path, 
        language: Optional[str] = None
    ) -> dict:
        """
        Transcribe audio file.
        
        Args:
            audio_path: Path to audio file
            language: Optional language code (es, en, etc.)
        
        Returns:
            dict with text, language, confidence
        """
        if not WHISPER_AVAILABLE or self.model is None:
            return {
                "text": "[Transcription not available - Whisper not installed]",
                "language": "unknown",
                "success": False,
                "error": "Whisper not available"
            }
        
        try:
            # Transcribe
            logger.info(f"Transcribing audio: {audio_path}")
            
            result = self.model.transcribe(
                str(audio_path),
                language=language,
                fp16=False,  # Use fp32 for CPU compatibility
            )
            
            text = result["text"].strip()
            detected_language = result.get("language", "unknown")
            
            logger.info(f"Transcription complete: {len(text)} chars, language={detected_language}")
            
            return {
                "text": text,
                "language": detected_language,
                "success": True,
                "confidence": 1.0,  # Whisper doesn't provide confidence
            }
        
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {
                "text": "",
                "language": "unknown",
                "success": False,
                "error": str(e)
            }
    
    async def transcribe_with_fallback(
        self,
        audio_path: Path,
        language: Optional[str] = "es"
    ) -> str:
        """
        Transcribe with fallback to error message.
        
        Returns just the text string.
        """
        result = await self.transcribe(audio_path, language)
        
        if result["success"]:
            return result["text"]
        else:
            return f"[Could not transcribe audio: {result.get('error', 'unknown error')}]"
```

**Tests:** `tests/unit/test_whisper_service.py`

---

### A3: Telegram Media Handlers

**File:** `src/app/telegram/handlers.py` (additions)

```python
from app.services.media_handler import MediaHandler
from app.integrations.whisper_service import WhisperService

class TelegramHandler:
    def __init__(self):
        # ... existing init ...
        self.media_handler = MediaHandler()
        self.whisper_service = WhisperService(model_name="base")
    
    async def handle_photo(self, update, context):
        """Handle photo messages."""
        message = update.message
        chat_id = str(message.chat_id)
        user_id = str(message.from_user.id)
        
        # Get the largest photo
        photo = message.photo[-1]
        
        # Download to temp file
        file = await context.bot.get_file(photo.file_id)
        temp_path = Path(f"/tmp/{photo.file_id}.jpg")
        await file.download_to_drive(temp_path)
        
        # Store media
        media_info = await self.media_handler.store_photo(temp_path, user_id)
        
        # Get caption (if any)
        caption = message.caption or "Photo"
        
        # Process with enrichment
        response = await self.orchestrator.handle_message(
            message=caption,
            chat_id=chat_id,
            user_id=user_id,
            metadata={
                "media_type": "photo",
                "media_path": media_info["media_path"],
                "file_size": media_info["file_size"],
            }
        )
        
        await message.reply_text(response)
        
        # Cleanup temp file
        temp_path.unlink()
    
    async def handle_voice(self, update, context):
        """Handle voice messages."""
        message = update.message
        chat_id = str(message.chat_id)
        user_id = str(message.from_user.id)
        
        # Download voice note
        voice = message.voice
        file = await context.bot.get_file(voice.file_id)
        temp_path = Path(f"/tmp/{voice.file_id}.ogg")
        await file.download_to_drive(temp_path)
        
        # Store media
        media_info = await self.media_handler.store_voice(temp_path, user_id)
        
        # Transcribe
        await message.reply_text("🎙️ Transcribiendo...")
        
        transcription = await self.whisper_service.transcribe_with_fallback(
            temp_path,
            language="es"
        )
        
        # Process with enrichment
        response = await self.orchestrator.handle_message(
            message=transcription,
            chat_id=chat_id,
            user_id=user_id,
            metadata={
                "media_type": "voice",
                "media_path": media_info["media_path"],
                "file_size": media_info["file_size"],
                "transcription": transcription,
            }
        )
        
        await message.reply_text(f"📝 Transcripción: {transcription}\n\n{response}")
        
        # Cleanup
        temp_path.unlink()
    
    async def handle_location(self, update, context):
        """Handle location shares."""
        message = update.message
        chat_id = str(message.chat_id)
        user_id = str(message.from_user.id)
        
        location = message.location
        
        # Store location data
        location_data = {
            "latitude": location.latitude,
            "longitude": location.longitude,
        }
        
        # Check if user is in enrichment conversation
        if await self.orchestrator.enrichment_agent.state_manager.has_context(chat_id):
            # Respond with coordinates
            response = await self.orchestrator.handle_message(
                message=f"Ubicación: {location.latitude}, {location.longitude}",
                chat_id=chat_id,
                user_id=user_id,
                metadata=location_data
            )
        else:
            # Create new note with location
            response = await self.orchestrator.handle_message(
                message="Guardar esta ubicación",
                chat_id=chat_id,
                user_id=user_id,
                metadata=location_data
            )
        
        await message.reply_text(response)
```

---

## 📊 Testing Plan

### Manual Testing Checklist

**C1: Basic Enrichment (30 min)**
- [ ] Add list item with enrichment
- [ ] Create task with enrichment
- [ ] Skip enrichment
- [ ] Cancel enrichment
- [ ] Multi-turn conversation

**C2: Media Workflows (1 hour)**
- [ ] Upload photo with caption
- [ ] Send voice note (Spanish)
- [ ] Send voice note (English)
- [ ] Upload document
- [ ] Share location
- [ ] Photo + enrichment flow
- [ ] Voice + enrichment flow

**C3: Edge Cases (1 hour)**
- [ ] Very long voice notes
- [ ] Poor audio quality
- [ ] Large files
- [ ] Unsupported file types
- [ ] Network failures
- [ ] Whisper not available
- [ ] Storage full scenarios

**C4: Spanish Language (30 min)**
- [ ] All prompts in Spanish
- [ ] Voice transcription accuracy
- [ ] Entity extraction in Spanish
- [ ] Error messages in Spanish

---

## 🚀 Production Deployment

### Environment Setup

**.env additions:**
```bash
# Media Storage
MEDIA_STORAGE_PATH=data/media
MAX_MEDIA_SIZE_MB=50

# Whisper
WHISPER_MODEL=base  # tiny, base, small, medium, large
WHISPER_LANGUAGE=es

# Monitoring
ENABLE_METRICS=true
METRICS_FILE=data/metrics.jsonl
```

### Deployment Checklist

- [ ] Install Whisper: `pip install openai-whisper`
- [ ] Create media storage directory
- [ ] Test with production Telegram token
- [ ] Verify all environment variables
- [ ] Test with real users (controlled rollout)
- [ ] Monitor error rates
- [ ] Set up backup/cleanup jobs
- [ ] Document user instructions

---

## 📈 Success Metrics

**Phase 3 Complete When:**
- [ ] Media handler fully implemented and tested
- [ ] Whisper transcription working (Spanish + English)
- [ ] Telegram handlers for photo/voice/location
- [ ] All manual testing completed
- [ ] Error handling comprehensive
- [ ] Documentation updated
- [ ] Deployed to production (limited rollout)
- [ ] No critical bugs in 48 hours
- [ ] User feedback collected

**Quality Gates:**
- All Phase 2 tests still passing
- New media tests passing
- Manual test checklist 100% complete
- Error rate < 5%
- Transcription accuracy > 80%
- Response time < 3s (including transcription)

---

## 📝 Next Steps After Phase 3

1. **Collect User Feedback** - Real usage patterns
2. **Phase 4: CrewAI Migration** - Start parallel track
3. **Phase 5: Advanced Features** - Based on feedback
4. **Analytics Dashboard** - Visualize usage patterns

---

**Ready to start implementing? Let me know and I'll begin with Part A (Media Handler)!** 🚀
