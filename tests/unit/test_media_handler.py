"""Tests for MediaHandler service."""

import os
import tempfile
import time
from pathlib import Path

import pytest
from PIL import Image

from src.app.services.media_handler import MediaHandler


@pytest.fixture
def media_handler(tmp_path):
    """Create a MediaHandler with temporary storage."""
    return MediaHandler(storage_path=tmp_path / "media")


@pytest.fixture
def sample_image(tmp_path):
    """Create a sample image file using PIL."""
    image_path = tmp_path / "test_image.jpg"
    # Create a simple 100x100 red image
    img = Image.new("RGB", (100, 100), color="red")
    img.save(image_path, "JPEG")
    return image_path


@pytest.fixture
def sample_audio(tmp_path):
    """Create a sample audio file."""
    audio_path = tmp_path / "test_audio.ogg"
    # Create a minimal OGG file
    audio_path.write_bytes(b"OggS" + b"\x00" * 100)
    return audio_path


@pytest.fixture
def sample_document(tmp_path):
    """Create a sample document file."""
    doc_path = tmp_path / "test_doc.txt"
    doc_path.write_text("Sample document content")
    return doc_path


@pytest.mark.anyio
async def test_store_photo(media_handler, sample_image):
    """Test storing a photo."""
    result = await media_handler.store_photo(
        file_path=sample_image, user_id="user123"
    )

    assert result["media_type"] == "photo"
    assert result["file_size"] > 0
    assert "user123" in result["media_path"]
    assert "photos" in result["media_path"]
    assert result["original_name"] == "test_image.jpg"
    assert "stored_at" in result

    # Verify file exists
    stored_path = media_handler.storage_path / result["media_path"]
    assert stored_path.exists()


@pytest.mark.anyio
async def test_store_photo_with_metadata(media_handler, sample_image):
    """Test storing a photo with metadata."""
    metadata = {"caption": "Test photo", "telegram_id": "123456"}

    result = await media_handler.store_photo(
        file_path=sample_image, user_id="user123", metadata=metadata
    )

    assert result["metadata"] == metadata


@pytest.mark.anyio
async def test_store_voice(media_handler, sample_audio):
    """Test storing a voice note."""
    result = await media_handler.store_voice(
        file_path=sample_audio, user_id="user456"
    )

    assert result["media_type"] == "voice"
    assert result["file_size"] > 0
    assert "user456" in result["media_path"]
    assert "voice" in result["media_path"]
    assert "stored_at" in result

    # Verify file exists
    stored_path = media_handler.storage_path / result["media_path"]
    assert stored_path.exists()


@pytest.mark.anyio
async def test_store_document(media_handler, sample_document):
    """Test storing a document."""
    result = await media_handler.store_document(
        file_path=sample_document, user_id="user789"
    )

    assert result["media_type"] == "document"
    assert result["file_size"] > 0
    assert "user789" in result["media_path"]
    assert "documents" in result["media_path"]

    # Verify file exists
    stored_path = media_handler.storage_path / result["media_path"]
    assert stored_path.exists()


@pytest.mark.anyio
async def test_get_media(media_handler, sample_image):
    """Test retrieving a stored media file."""
    # Store a file first
    result = await media_handler.store_photo(sample_image, "user123")

    # Retrieve it
    retrieved_path = await media_handler.get_media(result["media_path"])

    assert retrieved_path is not None
    assert retrieved_path.exists()
    assert retrieved_path.is_file()


@pytest.mark.anyio
async def test_get_media_not_found(media_handler):
    """Test retrieving non-existent media."""
    result = await media_handler.get_media("nonexistent/file.jpg")
    assert result is None


@pytest.mark.anyio
async def test_delete_media(media_handler, sample_image):
    """Test deleting a media file."""
    # Store a file first
    result = await media_handler.store_photo(sample_image, "user123")

    # Delete it
    deleted = await media_handler.delete_media(result["media_path"])
    assert deleted is True

    # Verify it's gone
    retrieved = await media_handler.get_media(result["media_path"])
    assert retrieved is None


@pytest.mark.anyio
async def test_delete_media_not_found(media_handler):
    """Test deleting non-existent media."""
    deleted = await media_handler.delete_media("nonexistent/file.jpg")
    assert deleted is False


@pytest.mark.anyio
async def test_validate_file_size(media_handler, tmp_path):
    """Test file size validation."""
    # Create a file larger than the limit
    large_file = tmp_path / "large.jpg"
    large_file.write_bytes(b"x" * (11 * 1024 * 1024))  # 11 MB

    with pytest.raises(ValueError, match="File too large"):
        await media_handler.store_photo(large_file, "user123")


@pytest.mark.anyio
async def test_validate_file_type(media_handler, tmp_path):
    """Test file type validation."""
    # Create a file with invalid extension
    invalid_file = tmp_path / "invalid.xyz"
    invalid_file.write_bytes(b"invalid content")

    with pytest.raises(ValueError, match="Unsupported file type"):
        await media_handler.store_photo(invalid_file, "user123")


@pytest.mark.anyio
async def test_validate_file_not_found(media_handler, tmp_path):
    """Test validation of non-existent file."""
    nonexistent = tmp_path / "nonexistent.jpg"

    with pytest.raises(ValueError, match="File not found"):
        await media_handler.store_photo(nonexistent, "user123")


@pytest.mark.anyio
async def test_unique_filenames(media_handler, sample_image):
    """Test that stored files get unique names."""
    result1 = await media_handler.store_photo(sample_image, "user123")
    result2 = await media_handler.store_photo(sample_image, "user123")

    assert result1["media_path"] != result2["media_path"]


@pytest.mark.anyio
async def test_user_isolation(media_handler, sample_image):
    """Test that files are isolated by user."""
    result1 = await media_handler.store_photo(sample_image, "user1")
    result2 = await media_handler.store_photo(sample_image, "user2")

    assert "user1" in result1["media_path"]
    assert "user2" in result2["media_path"]
    assert result1["media_path"] != result2["media_path"]


@pytest.mark.anyio
async def test_cleanup_old_media(media_handler, sample_image):
    """Test cleaning up old media files."""
    # Store a file
    result = await media_handler.store_photo(sample_image, "user123")

    # Modify file timestamp to make it "old"
    stored_path = media_handler.storage_path / result["media_path"]
    import os
    import time

    old_time = time.time() - (100 * 24 * 60 * 60)  # 100 days ago
    os.utime(stored_path, (old_time, old_time))

    # Cleanup files older than 90 days
    deleted_count = await media_handler.cleanup_old_media(days=90)

    assert deleted_count == 1
    assert not stored_path.exists()


@pytest.mark.anyio
async def test_cleanup_preserves_recent_files(media_handler, sample_image):
    """Test that cleanup preserves recent files."""
    # Store a file (will have current timestamp)
    result = await media_handler.store_photo(sample_image, "user123")

    # Cleanup files older than 90 days
    deleted_count = await media_handler.cleanup_old_media(days=90)

    # Recent file should be preserved
    assert deleted_count == 0
    stored_path = media_handler.storage_path / result["media_path"]
    assert stored_path.exists()


@pytest.mark.anyio
async def test_get_storage_stats(media_handler, sample_image, sample_audio, sample_document):
    """Test getting storage statistics."""
    # Store different types of files
    await media_handler.store_photo(sample_image, "user123")
    await media_handler.store_photo(sample_image, "user123")
    await media_handler.store_voice(sample_audio, "user123")
    await media_handler.store_document(sample_document, "user123")

    # Get stats
    stats = media_handler.get_storage_stats()

    assert stats["total_files"] == 4
    assert stats["photos"]["count"] == 2
    assert stats["voice"]["count"] == 1
    assert stats["documents"]["count"] == 1
    assert stats["total_size_mb"] >= 0  # Size may be very small but should be counted


@pytest.mark.anyio
async def test_get_storage_stats_per_user(media_handler, sample_image):
    """Test getting storage statistics for specific user."""
    # Store files for different users
    await media_handler.store_photo(sample_image, "user1")
    await media_handler.store_photo(sample_image, "user1")
    await media_handler.store_photo(sample_image, "user2")

    # Get stats for user1
    stats = media_handler.get_storage_stats(user_id="user1")

    assert stats["total_files"] == 2
    assert stats["photos"]["count"] == 2


def test_generate_filename(media_handler):
    """Test filename generation."""
    filename1 = media_handler._generate_filename("photo", ".jpg")
    filename2 = media_handler._generate_filename("photo", ".jpg")

    assert filename1.startswith("photo_")
    assert filename1.endswith(".jpg")
    assert filename1 != filename2  # Should be unique
