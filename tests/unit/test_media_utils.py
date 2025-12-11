"""Tests for media reference extraction and handling."""

import pytest
from app.utils import MediaReference, extract_media_reference, format_media_display


class TestMediaReferenceExtraction:
    """Test media reference extraction from messages."""

    def test_extract_photo_with_path(self):
        """Test extracting photo reference with path."""
        message = "[Photo: media/user123/photos/photo_123.jpg] My new car"
        clean_msg, media_ref = extract_media_reference(message)
        
        assert clean_msg == "My new car"
        assert media_ref is not None
        assert media_ref.media_type == "photo"
        assert media_ref.media_path == "media/user123/photos/photo_123.jpg"
        assert media_ref.clean_message == "My new car"

    def test_extract_photo_legacy(self):
        """Test extracting photo reference without path (legacy)."""
        message = "[Photo attached] Beautiful sunset"
        clean_msg, media_ref = extract_media_reference(message)
        
        assert clean_msg == "Beautiful sunset"
        assert media_ref is not None
        assert media_ref.media_type == "photo"
        assert media_ref.media_path is None
        assert media_ref.clean_message == "Beautiful sunset"

    def test_extract_voice_with_path(self):
        """Test extracting voice reference with path."""
        message = "[Voice: media/user123/voice/voice_456.ogg] Remind me to call mom tomorrow"
        clean_msg, media_ref = extract_media_reference(message)
        
        assert clean_msg == "Remind me to call mom tomorrow"
        assert media_ref is not None
        assert media_ref.media_type == "voice"
        assert media_ref.media_path == "media/user123/voice/voice_456.ogg"

    def test_extract_voice_legacy(self):
        """Test extracting voice reference without path (legacy)."""
        message = "[Voice note] Buy milk and eggs"
        clean_msg, media_ref = extract_media_reference(message)
        
        assert clean_msg == "Buy milk and eggs"
        assert media_ref is not None
        assert media_ref.media_type == "voice"
        assert media_ref.media_path is None

    def test_extract_document_with_path(self):
        """Test extracting document reference with path."""
        message = "[Document: contract.pdf | media/user123/documents/doc_789.pdf] Review this please"
        clean_msg, media_ref = extract_media_reference(message)
        
        assert clean_msg == "Review this please"
        assert media_ref is not None
        assert media_ref.media_type == "document"
        assert media_ref.filename == "contract.pdf"
        assert media_ref.media_path == "media/user123/documents/doc_789.pdf"

    def test_extract_document_legacy(self):
        """Test extracting document reference without path (legacy)."""
        message = "[Document: report.docx] Please check"
        clean_msg, media_ref = extract_media_reference(message)
        
        assert clean_msg == "Please check"
        assert media_ref is not None
        assert media_ref.media_type == "document"
        assert media_ref.filename == "report.docx"
        assert media_ref.media_path is None

    def test_extract_location(self):
        """Test extracting location reference."""
        message = "[Location: lat=40.7128, lon=-74.0060] I'm at the office"
        clean_msg, media_ref = extract_media_reference(message)
        
        assert clean_msg == "I'm at the office"
        assert media_ref is not None
        assert media_ref.media_type == "location"
        assert media_ref.latitude == 40.7128
        assert media_ref.longitude == -74.0060

    def test_extract_no_media(self):
        """Test message without media reference."""
        message = "Just a regular message"
        clean_msg, media_ref = extract_media_reference(message)
        
        assert clean_msg == "Just a regular message"
        assert media_ref is None

    def test_extract_empty_caption(self):
        """Test media with empty caption."""
        message = "[Photo: media/photo.jpg] "
        clean_msg, media_ref = extract_media_reference(message)
        
        assert clean_msg == ""
        assert media_ref is not None
        assert media_ref.media_type == "photo"

    def test_format_media_display_photo(self):
        """Test formatting photo for display."""
        media_ref = MediaReference(
            media_type="photo",
            clean_message="test",
            media_path="photo.jpg"
        )
        display = format_media_display(media_ref)
        assert display == "📷 Photo"

    def test_format_media_display_voice(self):
        """Test formatting voice for display."""
        media_ref = MediaReference(
            media_type="voice",
            clean_message="test",
            media_path="voice.ogg"
        )
        display = format_media_display(media_ref)
        assert display == "🎤 Voice note"

    def test_format_media_display_document(self):
        """Test formatting document for display."""
        media_ref = MediaReference(
            media_type="document",
            clean_message="test",
            filename="contract.pdf"
        )
        display = format_media_display(media_ref)
        assert display == "📄 contract.pdf"

    def test_format_media_display_location(self):
        """Test formatting location for display."""
        media_ref = MediaReference(
            media_type="location",
            clean_message="test",
            latitude=40.7128,
            longitude=-74.0060
        )
        display = format_media_display(media_ref)
        assert display == "📍 40.7128, -74.006"


class TestMediaReferenceToDict:
    """Test MediaReference serialization."""

    def test_to_dict_photo(self):
        """Test serializing photo reference."""
        media_ref = MediaReference(
            media_type="photo",
            clean_message="test",
            media_path="photo.jpg"
        )
        data = media_ref.to_dict()
        
        assert data["media_type"] == "photo"
        assert data["media_path"] == "photo.jpg"
        assert "latitude" not in data
        assert "longitude" not in data

    def test_to_dict_location(self):
        """Test serializing location reference."""
        media_ref = MediaReference(
            media_type="location",
            clean_message="test",
            latitude=40.7128,
            longitude=-74.0060
        )
        data = media_ref.to_dict()
        
        assert data["media_type"] == "location"
        assert data["latitude"] == 40.7128
        assert data["longitude"] == -74.0060
        assert "media_path" not in data

    def test_to_dict_document(self):
        """Test serializing document reference."""
        media_ref = MediaReference(
            media_type="document",
            clean_message="test",
            filename="report.pdf",
            media_path="docs/report.pdf"
        )
        data = media_ref.to_dict()
        
        assert data["media_type"] == "document"
        assert data["filename"] == "report.pdf"
        assert data["media_path"] == "docs/report.pdf"
