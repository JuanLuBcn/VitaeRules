"""Utilities for extracting and handling media references in messages."""

import re
from typing import Optional


class MediaReference:
    """Represents a media reference extracted from a message."""

    def __init__(
        self,
        media_type: str,
        clean_message: str,
        media_path: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        filename: Optional[str] = None,
    ):
        """
        Initialize media reference.

        Args:
            media_type: Type of media (photo, voice, document, location)
            clean_message: Message with media prefix removed
            media_path: Path to stored media file (for photo/voice/document)
            latitude: Latitude (for location)
            longitude: Longitude (for location)
            filename: Original filename (for document)
        """
        self.media_type = media_type
        self.clean_message = clean_message
        self.media_path = media_path
        self.latitude = latitude
        self.longitude = longitude
        self.filename = filename

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        data = {
            "media_type": self.media_type,
        }
        if self.media_path:
            data["media_path"] = self.media_path
        if self.latitude is not None:
            data["latitude"] = self.latitude
        if self.longitude is not None:
            data["longitude"] = self.longitude
        if self.filename:
            data["filename"] = self.filename
        return data

    def __repr__(self) -> str:
        """String representation."""
        if self.media_type == "location":
            return f"MediaReference(location: {self.latitude}, {self.longitude})"
        return f"MediaReference({self.media_type}: {self.media_path})"


def extract_media_reference(message: str) -> tuple[str, Optional[MediaReference]]:
    """
    Extract media reference from a message.

    Detects special prefixes added by Telegram handlers:
    - [Photo: path/to/file] caption
    - [Photo attached] caption (legacy, no path)
    - [Voice: path/to/file] transcription
    - [Voice note] transcription (legacy, no path)
    - [Document: filename.pdf | path/to/file] description
    - [Document: filename.pdf] description (legacy, no path)
    - [Location: lat=X, lon=Y] context

    Args:
        message: Message that may contain media reference

    Returns:
        Tuple of (clean_message, media_reference or None)
    """
    # Pattern for photo with path
    photo_path_match = re.match(r"\[Photo:\s*([^\]]+)\]\s*(.*)", message, re.IGNORECASE)
    if photo_path_match:
        media_path = photo_path_match.group(1).strip()
        clean_msg = photo_path_match.group(2).strip()
        return (
            clean_msg,
            MediaReference(
                media_type="photo",
                clean_message=clean_msg,
                media_path=media_path,
            ),
        )
    
    # Pattern for photo (legacy)
    photo_match = re.match(r"\[Photo attached\]\s*(.*)", message, re.IGNORECASE)
    if photo_match:
        clean_msg = photo_match.group(1).strip()
        return (
            clean_msg,
            MediaReference(
                media_type="photo",
                clean_message=clean_msg,
            ),
        )

    # Pattern for voice with path
    voice_path_match = re.match(r"\[Voice:\s*([^\]]+)\]\s*(.*)", message, re.IGNORECASE)
    if voice_path_match:
        media_path = voice_path_match.group(1).strip()
        clean_msg = voice_path_match.group(2).strip()
        return (
            clean_msg,
            MediaReference(
                media_type="voice",
                clean_message=clean_msg,
                media_path=media_path,
            ),
        )

    # Pattern for voice note (legacy)
    voice_match = re.match(r"\[Voice note\]\s*(.*)", message, re.IGNORECASE)
    if voice_match:
        clean_msg = voice_match.group(1).strip()
        return (
            clean_msg,
            MediaReference(
                media_type="voice",
                clean_message=clean_msg,
            ),
        )

    # Pattern for document with path
    doc_path_match = re.match(
        r"\[Document:\s*([^|]+)\|\s*([^\]]+)\]\s*(.*)", message, re.IGNORECASE
    )
    if doc_path_match:
        filename = doc_path_match.group(1).strip()
        media_path = doc_path_match.group(2).strip()
        clean_msg = doc_path_match.group(3).strip()
        return (
            clean_msg,
            MediaReference(
                media_type="document",
                clean_message=clean_msg,
                filename=filename,
                media_path=media_path,
            ),
        )

    # Pattern for document (legacy)
    doc_match = re.match(
        r"\[Document:\s*([^\]]+)\]\s*(.*)", message, re.IGNORECASE
    )
    if doc_match:
        filename = doc_match.group(1).strip()
        clean_msg = doc_match.group(2).strip()
        return (
            clean_msg,
            MediaReference(
                media_type="document",
                clean_message=clean_msg,
                filename=filename,
            ),
        )

    # Pattern for location
    loc_match = re.match(
        r"\[Location:\s*lat=([-\d.]+),\s*lon=([-\d.]+)\]\s*(.*)",
        message,
        re.IGNORECASE,
    )
    if loc_match:
        lat = float(loc_match.group(1))
        lon = float(loc_match.group(2))
        clean_msg = loc_match.group(3).strip()
        return (
            clean_msg,
            MediaReference(
                media_type="location",
                clean_message=clean_msg,
                latitude=lat,
                longitude=lon,
            ),
        )

    # No media reference found
    return (message, None)


def format_media_display(media_ref: MediaReference) -> str:
    """
    Format media reference for display to user.

    Args:
        media_ref: Media reference to format

    Returns:
        Formatted string with emoji and info
    """
    if media_ref.media_type == "photo":
        return "📷 Photo"
    elif media_ref.media_type == "voice":
        return "🎤 Voice note"
    elif media_ref.media_type == "document":
        if media_ref.filename:
            return f"📄 {media_ref.filename}"
        return "📄 Document"
    elif media_ref.media_type == "location":
        if media_ref.latitude and media_ref.longitude:
            return f"📍 {media_ref.latitude}, {media_ref.longitude}"
        return "📍 Location"
    return ""
