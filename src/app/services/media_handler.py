"""Media file storage and management service."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

# Try to import PIL for image processing (optional)
try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Try to import config and tracing (optional for testing)
try:
    from ..config import get_settings
    from ..tracing import get_tracer

    _logger = get_tracer()
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    _logger = None


def _log(level: str, message: str):
    """Helper to log only if logger is available."""
    if _logger:
        getattr(_logger, level)(message)


class MediaHandler:
    """Handle media file storage, retrieval, and management."""

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize media handler.

        Args:
            storage_path: Root directory for media storage (default: from settings)
        """
        if storage_path:
            self.storage_path = storage_path
        elif CONFIG_AVAILABLE:
            self.settings = get_settings()
            # Use the storage_path from settings (data/storage) as base for media
            self.storage_path = Path(self.settings.storage_path) / "media"
        else:
            # Default for testing
            self.storage_path = Path("./data/media")

        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Size limits (in MB)
        self.max_image_size_mb = 10
        self.max_audio_size_mb = 20
        self.max_document_size_mb = 50

        # Supported file types
        self.image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        self.audio_extensions = {".ogg", ".mp3", ".wav", ".m4a", ".opus"}
        self.document_extensions = {".pdf", ".txt", ".doc", ".docx"}

        _log("info", f"MediaHandler initialized at {self.storage_path}")

    async def store_photo(
        self, file_path: Path, user_id: str, metadata: Optional[dict] = None
    ) -> dict:
        """
        Store a photo file.

        Args:
            file_path: Temporary file path from Telegram
            user_id: User identifier
            metadata: Optional metadata (caption, timestamp, etc.)

        Returns:
            dict with media_path, thumbnail_path, size, etc.

        Raises:
            ValueError: If file is too large or invalid type
        """
        # Validate file
        self._validate_file(file_path, self.max_image_size_mb, self.image_extensions)

        # Generate unique filename
        file_ext = file_path.suffix.lower()
        unique_name = self._generate_filename("photo", file_ext)

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
        if PIL_AVAILABLE:
            try:
                thumbnail_path = await self._create_thumbnail(final_path)
            except Exception as e:
                _log("warning", f"Could not create thumbnail: {e}")

        _log("info", f"Stored photo: {final_path} ({file_size} bytes)")

        return {
            "media_path": str(final_path.relative_to(self.storage_path)),
            "thumbnail_path": (
                str(thumbnail_path.relative_to(self.storage_path))
                if thumbnail_path
                else None
            ),
            "file_size": file_size,
            "media_type": "photo",
            "original_name": file_path.name,
            "stored_at": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

    async def store_voice(
        self, file_path: Path, user_id: str, metadata: Optional[dict] = None
    ) -> dict:
        """
        Store a voice note file.

        Args:
            file_path: Temporary file path from Telegram
            user_id: User identifier
            metadata: Optional metadata (duration, transcription, etc.)

        Returns:
            dict with media_path, size, etc.

        Raises:
            ValueError: If file is too large or invalid type
        """
        # Validate file
        self._validate_file(file_path, self.max_audio_size_mb, self.audio_extensions)

        # Generate unique filename
        file_ext = file_path.suffix.lower() or ".ogg"
        unique_name = self._generate_filename("voice", file_ext)

        # User-specific directory
        user_dir = self.storage_path / user_id / "voice"
        user_dir.mkdir(parents=True, exist_ok=True)

        final_path = user_dir / unique_name

        # Copy file
        shutil.copy2(file_path, final_path)

        # Get file info
        file_size = final_path.stat().st_size

        _log("info", f"Stored voice note: {final_path} ({file_size} bytes)")

        return {
            "media_path": str(final_path.relative_to(self.storage_path)),
            "file_size": file_size,
            "media_type": "voice",
            "original_name": file_path.name,
            "stored_at": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

    async def store_document(
        self, file_path: Path, user_id: str, metadata: Optional[dict] = None
    ) -> dict:
        """
        Store a document file.

        Args:
            file_path: Temporary file path from Telegram
            user_id: User identifier
            metadata: Optional metadata (mime_type, etc.)

        Returns:
            dict with media_path, size, etc.

        Raises:
            ValueError: If file is too large or invalid type
        """
        # Validate file
        self._validate_file(
            file_path, self.max_document_size_mb, self.document_extensions
        )

        # Generate unique filename
        file_ext = file_path.suffix.lower()
        unique_name = self._generate_filename("doc", file_ext)

        # User-specific directory
        user_dir = self.storage_path / user_id / "documents"
        user_dir.mkdir(parents=True, exist_ok=True)

        final_path = user_dir / unique_name

        # Copy file
        shutil.copy2(file_path, final_path)

        # Get file info
        file_size = final_path.stat().st_size

        _log("info", f"Stored document: {final_path} ({file_size} bytes)")

        return {
            "media_path": str(final_path.relative_to(self.storage_path)),
            "file_size": file_size,
            "media_type": "document",
            "original_name": file_path.name,
            "stored_at": datetime.now().isoformat(),
            "metadata": metadata or {},
        }

    async def get_media(self, media_path: str) -> Optional[Path]:
        """
        Retrieve media file by relative path.

        Args:
            media_path: Relative path from storage root

        Returns:
            Full path to media file, or None if not found
        """
        full_path = self.storage_path / media_path

        if full_path.exists() and full_path.is_file():
            return full_path

        _log("warning", f"Media not found: {media_path}")
        return None

    async def delete_media(self, media_path: str) -> bool:
        """
        Delete a media file.

        Args:
            media_path: Relative path from storage root

        Returns:
            True if deleted, False if not found
        """
        full_path = self.storage_path / media_path

        if full_path.exists() and full_path.is_file():
            full_path.unlink()
            _log("info", f"Deleted media: {media_path}")

            # Also delete thumbnail if it exists
            if "photos/" in media_path:
                thumbnail_path = self._get_thumbnail_path(full_path)
                if thumbnail_path and thumbnail_path.exists():
                    thumbnail_path.unlink()
                    _log("debug", f"Deleted thumbnail: {thumbnail_path}")

            return True

        _log("warning", f"Media not found for deletion: {media_path}")
        return False

    async def cleanup_old_media(self, days: int = 90, user_id: Optional[str] = None) -> int:
        """
        Delete media files older than specified days.

        Args:
            days: Delete files older than this many days
            user_id: Optional - only clean up for specific user

        Returns:
            Number of files deleted
        """
        cutoff_timestamp = datetime.now().timestamp() - (days * 24 * 60 * 60)
        deleted_count = 0

        # Determine search path
        search_path = (
            self.storage_path / user_id if user_id else self.storage_path
        )

        if not search_path.exists():
            _log("warning", f"Search path does not exist: {search_path}")
            return 0

        # Find and delete old files
        for media_file in search_path.rglob("*"):
            if media_file.is_file() and "thumbnails" not in str(media_file):
                if media_file.stat().st_mtime < cutoff_timestamp:
                    try:
                        media_file.unlink()
                        deleted_count += 1
                        _log("debug", f"Deleted old media: {media_file}")
                    except Exception as e:
                        _log("error", f"Failed to delete {media_file}: {e}")

        _log("info", 
            f"Cleaned up {deleted_count} old media files (older than {days} days)"
        )
        return deleted_count

    def _generate_filename(self, prefix: str, extension: str) -> str:
        """
        Generate a unique filename.

        Args:
            prefix: Filename prefix (photo, voice, doc)
            extension: File extension with dot

        Returns:
            Unique filename
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid4().hex[:8]
        return f"{prefix}_{timestamp}_{unique_id}{extension}"

    def _validate_file(
        self, file_path: Path, max_size_mb: float, allowed_extensions: set
    ) -> None:
        """
        Validate file size and type.

        Args:
            file_path: Path to file
            max_size_mb: Maximum allowed size in MB
            allowed_extensions: Set of allowed file extensions

        Raises:
            ValueError: If file is invalid
        """
        # Check file exists
        if not file_path.exists():
            raise ValueError(f"File not found: {file_path}")

        # Check file size
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > max_size_mb:
            raise ValueError(
                f"File too large: {file_size_mb:.2f}MB (max: {max_size_mb}MB)"
            )

        # Check file extension
        file_ext = file_path.suffix.lower()
        if file_ext not in allowed_extensions:
            raise ValueError(
                f"Unsupported file type: {file_ext} (allowed: {allowed_extensions})"
            )

    async def _create_thumbnail(
        self, image_path: Path, max_size: tuple = (200, 200)
    ) -> Optional[Path]:
        """
        Create a thumbnail for an image.

        Args:
            image_path: Path to original image
            max_size: Maximum thumbnail dimensions (width, height)

        Returns:
            Path to thumbnail, or None if failed
        """
        if not PIL_AVAILABLE:
            return None

        try:
            # Create thumbnails directory
            thumbnail_dir = image_path.parent / "thumbnails"
            thumbnail_dir.mkdir(exist_ok=True)

            # Generate thumbnail path
            thumbnail_path = thumbnail_dir / f"thumb_{image_path.name}"

            # Create thumbnail
            with Image.open(image_path) as img:
                # Convert to RGB if necessary (for PNG with transparency)
                if img.mode in ("RGBA", "LA", "P"):
                    background = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                    img = background

                # Create thumbnail
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                img.save(thumbnail_path, "JPEG", optimize=True, quality=85)

            _log("debug", f"Created thumbnail: {thumbnail_path}")
            return thumbnail_path

        except Exception as e:
            _log("warning", f"Failed to create thumbnail for {image_path}: {e}")
            return None

    def _get_thumbnail_path(self, image_path: Path) -> Optional[Path]:
        """Get the thumbnail path for an image."""
        thumbnail_dir = image_path.parent / "thumbnails"
        thumbnail_path = thumbnail_dir / f"thumb_{image_path.name}"
        return thumbnail_path if thumbnail_path.exists() else None

    def get_storage_stats(self, user_id: Optional[str] = None) -> dict:
        """
        Get storage statistics.

        Args:
            user_id: Optional - get stats for specific user

        Returns:
            dict with file counts and sizes by type
        """
        stats = {
            "total_files": 0,
            "total_size_mb": 0,
            "photos": {"count": 0, "size_mb": 0},
            "voice": {"count": 0, "size_mb": 0},
            "documents": {"count": 0, "size_mb": 0},
        }

        search_path = (
            self.storage_path / user_id if user_id else self.storage_path
        )

        if not search_path.exists():
            return stats

        for media_file in search_path.rglob("*"):
            if media_file.is_file() and "thumbnails" not in str(media_file):
                file_size_mb = media_file.stat().st_size / (1024 * 1024)
                stats["total_files"] += 1
                stats["total_size_mb"] += file_size_mb

                # Categorize by parent directory name (OS-agnostic)
                parent_name = media_file.parent.name
                if parent_name == "photos":
                    stats["photos"]["count"] += 1
                    stats["photos"]["size_mb"] += file_size_mb
                elif parent_name == "voice":
                    stats["voice"]["count"] += 1
                    stats["voice"]["size_mb"] += file_size_mb
                elif parent_name == "documents":
                    stats["documents"]["count"] += 1
                    stats["documents"]["size_mb"] += file_size_mb

        # Round sizes
        stats["total_size_mb"] = round(stats["total_size_mb"], 2)
        for category in ["photos", "voice", "documents"]:
            stats[category]["size_mb"] = round(stats[category]["size_mb"], 2)

        return stats
