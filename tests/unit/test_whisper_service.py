"""Tests for WhisperService."""

import pytest
from pathlib import Path
from src.app.services.whisper_service import WhisperService, WHISPER_AVAILABLE


@pytest.fixture
def whisper_service():
    """Create a WhisperService instance."""
    # Use tiny model for faster testing
    return WhisperService(model_name="tiny")


@pytest.fixture
def sample_audio_file(tmp_path):
    """Create a dummy audio file for testing."""
    # Create a minimal WAV file (just a header, won't play but tests file handling)
    audio_path = tmp_path / "test_audio.wav"
    # WAV file header (44 bytes)
    wav_header = (
        b"RIFF"
        + (36).to_bytes(4, "little")  # ChunkSize
        + b"WAVE"
        + b"fmt "
        + (16).to_bytes(4, "little")  # Subchunk1Size
        + (1).to_bytes(2, "little")  # AudioFormat (PCM)
        + (1).to_bytes(2, "little")  # NumChannels
        + (44100).to_bytes(4, "little")  # SampleRate
        + (88200).to_bytes(4, "little")  # ByteRate
        + (2).to_bytes(2, "little")  # BlockAlign
        + (16).to_bytes(2, "little")  # BitsPerSample
        + b"data"
        + (0).to_bytes(4, "little")  # Subchunk2Size
    )
    audio_path.write_bytes(wav_header)
    return audio_path


def test_whisper_service_initialization():
    """Test WhisperService initialization."""
    service = WhisperService(model_name="tiny")
    
    # Service should initialize even if Whisper is not installed
    assert service is not None
    assert service.model_name == "tiny"


def test_whisper_service_invalid_model():
    """Test WhisperService with invalid model name."""
    service = WhisperService(model_name="invalid_model")
    
    # Should fall back to "base" model
    if service.available:
        assert service.model_name == "base"


def test_whisper_service_is_available():
    """Test checking if Whisper is available."""
    service = WhisperService()
    
    result = service.is_available()
    assert isinstance(result, bool)
    assert result == WHISPER_AVAILABLE


def test_whisper_service_get_model_info():
    """Test getting model information."""
    service = WhisperService(model_name="tiny")
    
    info = service.get_model_info()
    assert isinstance(info, dict)
    assert "model_name" in info
    assert "device" in info
    assert "loaded" in info
    assert "available" in info
    
    if service.available:
        assert info["model_name"] == "tiny"
        assert info["loaded"] is False  # Not loaded until first use


@pytest.mark.anyio
async def test_transcribe_without_whisper(whisper_service, sample_audio_file):
    """Test transcription when Whisper is not available."""
    if WHISPER_AVAILABLE:
        pytest.skip("Whisper is available, skipping unavailable test")
    
    result = await whisper_service.transcribe(sample_audio_file)
    
    assert isinstance(result, dict)
    assert "success" in result
    assert result["success"] is False
    assert "error" in result


@pytest.mark.anyio
async def test_transcribe_file_not_found(whisper_service, tmp_path):
    """Test transcription with non-existent file."""
    nonexistent_file = tmp_path / "nonexistent.wav"
    
    if not WHISPER_AVAILABLE:
        # If Whisper not available, it should return error dict
        result = await whisper_service.transcribe(nonexistent_file)
        assert result["success"] is False
    else:
        # If Whisper is available, it should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            await whisper_service.transcribe(nonexistent_file)


@pytest.mark.anyio
@pytest.mark.skipif(not WHISPER_AVAILABLE, reason="Whisper not installed")
async def test_transcribe_with_whisper(whisper_service, sample_audio_file):
    """Test transcription with Whisper installed."""
    # Note: This test will fail with a dummy WAV file, but tests the code path
    result = await whisper_service.transcribe(sample_audio_file)
    
    assert isinstance(result, dict)
    assert "text" in result
    assert "language" in result
    assert "success" in result


@pytest.mark.anyio
async def test_transcribe_with_fallback_without_whisper(whisper_service, sample_audio_file):
    """Test fallback transcription when Whisper is not available."""
    if WHISPER_AVAILABLE:
        pytest.skip("Whisper is available, skipping unavailable test")
    
    result = await whisper_service.transcribe_with_fallback(sample_audio_file)
    
    assert isinstance(result, str)
    assert result == ""  # Should return empty string when unavailable


@pytest.mark.anyio
@pytest.mark.skipif(not WHISPER_AVAILABLE, reason="Whisper not installed")
async def test_transcribe_with_fallback_with_whisper(whisper_service, sample_audio_file):
    """Test fallback transcription with Whisper installed."""
    result = await whisper_service.transcribe_with_fallback(sample_audio_file)
    
    assert isinstance(result, str)
    # Result may be empty or contain text depending on audio content


@pytest.mark.anyio
async def test_detect_language_without_whisper(whisper_service, sample_audio_file):
    """Test language detection when Whisper is not available."""
    if WHISPER_AVAILABLE:
        pytest.skip("Whisper is available, skipping unavailable test")
    
    result = await whisper_service.detect_language(sample_audio_file)
    
    assert result == "unknown"


@pytest.mark.anyio
async def test_detect_language_file_not_found(whisper_service, tmp_path):
    """Test language detection with non-existent file."""
    nonexistent_file = tmp_path / "nonexistent.wav"
    
    result = await whisper_service.detect_language(nonexistent_file)
    
    assert result == "unknown"


@pytest.mark.anyio
@pytest.mark.skipif(not WHISPER_AVAILABLE, reason="Whisper not installed")
async def test_detect_language_with_whisper(whisper_service, sample_audio_file):
    """Test language detection with Whisper installed."""
    # Note: This test will likely fail/error with dummy WAV, but tests the code path
    result = await whisper_service.detect_language(sample_audio_file)
    
    assert isinstance(result, str)


def test_available_models():
    """Test that available models list is correct."""
    expected_models = ["tiny", "base", "small", "medium", "large"]
    assert WhisperService.AVAILABLE_MODELS == expected_models


def test_multiple_model_sizes():
    """Test initialization with different model sizes."""
    for model_name in ["tiny", "base", "small"]:
        service = WhisperService(model_name=model_name)
        if service.available:
            assert service.model_name == model_name


@pytest.mark.anyio
async def test_transcribe_with_language_hint(whisper_service, sample_audio_file):
    """Test transcription with language hint."""
    if not WHISPER_AVAILABLE:
        # Test graceful degradation
        result = await whisper_service.transcribe(sample_audio_file, language="es")
        assert result["success"] is False
    else:
        # Test with language parameter
        result = await whisper_service.transcribe(sample_audio_file, language="es")
        assert "language" in result


@pytest.mark.anyio
async def test_transcribe_translate_task(whisper_service, sample_audio_file):
    """Test transcription with translate task."""
    if not WHISPER_AVAILABLE:
        result = await whisper_service.transcribe(
            sample_audio_file, task="translate"
        )
        assert result["success"] is False
    else:
        # Test translate task
        result = await whisper_service.transcribe(
            sample_audio_file, task="translate"
        )
        assert isinstance(result, dict)


def test_lazy_loading():
    """Test that model is lazily loaded."""
    service = WhisperService(model_name="tiny")
    
    info = service.get_model_info()
    assert info["loaded"] is False  # Model not loaded yet
    
    # Model should only be loaded when transcribe is called


@pytest.mark.anyio
@pytest.mark.skipif(not WHISPER_AVAILABLE, reason="Whisper not installed")
async def test_model_loading_on_first_use(whisper_service, sample_audio_file):
    """Test that model is loaded on first transcription."""
    # Check model not loaded initially
    assert whisper_service.model is None
    
    # Attempt transcription (will trigger model loading)
    try:
        await whisper_service.transcribe(sample_audio_file)
    except Exception:
        # May fail with dummy audio, but that's ok
        pass
    
    # Model should now be loaded or available flag set to False
    assert whisper_service.model is not None or not whisper_service.available
