"""Whisper-based audio transcription service."""

from pathlib import Path
from typing import Optional

# Try to import Whisper (optional)
try:
    import whisper

    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

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


class WhisperService:
    """Handle audio transcription using Whisper."""

    # Model sizes: tiny, base, small, medium, large
    # Trade-off: smaller = faster but less accurate, larger = slower but more accurate
    AVAILABLE_MODELS = ["tiny", "base", "small", "medium", "large"]

    def __init__(self, model_name: str = "base", device: Optional[str] = None):
        """
        Initialize Whisper service.

        Args:
            model_name: Whisper model size (tiny, base, small, medium, large)
            device: Device to run on ("cpu", "cuda", or None for auto-detect)
        """
        # Validate model name
        if model_name not in self.AVAILABLE_MODELS:
            _log("warning", f"Invalid model '{model_name}'. Using 'base' instead.")
            model_name = "base"

        self.model_name = model_name
        self.device = device
        self.model = None

        if not WHISPER_AVAILABLE:
            _log("warning", "Whisper not available. Install with: pip install openai-whisper")
            self.available = False
            return

        self.available = True
        _log("info", f"WhisperService initialized with model '{model_name}'")

    def _load_model(self):
        """Lazy load the Whisper model."""
        if not self.available:
            raise RuntimeError("Whisper is not available")

        if self.model is None:
            _log("info", f"Loading Whisper model '{self.model_name}'...")
            try:
                self.model = whisper.load_model(self.model_name, device=self.device)
                _log("info", f"Whisper model '{self.model_name}' loaded successfully")
            except Exception as e:
                _log("error", f"Failed to load Whisper model: {e}")
                self.available = False
                raise

    async def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        task: str = "transcribe",
    ) -> dict:
        """
        Transcribe audio file.

        Args:
            audio_path: Path to audio file
            language: Language code (e.g., "en", "es") or None for auto-detect
            task: "transcribe" or "translate" (to English)

        Returns:
            dict with:
                - text: Transcribed text
                - language: Detected/specified language
                - segments: List of timestamped segments (optional)
                - success: bool

        Raises:
            RuntimeError: If Whisper is not available
            FileNotFoundError: If audio file doesn't exist
        """
        if not self.available:
            return {
                "text": "",
                "language": language or "unknown",
                "success": False,
                "error": "Whisper not available",
            }

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Load model if not already loaded
        self._load_model()

        _log("info", f"Transcribing audio: {audio_path}")

        try:
            # Run transcription
            result = self.model.transcribe(
                str(audio_path),
                language=language,
                task=task,
                verbose=False,
            )

            transcription = {
                "text": result["text"].strip(),
                "language": result.get("language", language or "unknown"),
                "segments": result.get("segments", []),
                "success": True,
            }

            _log(
                "info",
                f"Transcription complete: {len(transcription['text'])} chars, "
                f"language: {transcription['language']}",
            )

            return transcription

        except Exception as e:
            _log("error", f"Transcription failed: {e}")
            return {
                "text": "",
                "language": language or "unknown",
                "success": False,
                "error": str(e),
            }

    async def transcribe_with_fallback(
        self, audio_path: Path, preferred_language: Optional[str] = None
    ) -> str:
        """
        Transcribe audio with graceful fallback.

        This is a simplified version that just returns the text or empty string.
        Useful for when you don't need detailed metadata.

        Args:
            audio_path: Path to audio file
            preferred_language: Preferred language for transcription

        Returns:
            Transcribed text (or empty string if failed)
        """
        if not self.available:
            _log("warning", "Whisper not available, cannot transcribe audio")
            return ""

        result = await self.transcribe(audio_path, language=preferred_language)
        return result.get("text", "")

    async def detect_language(self, audio_path: Path) -> str:
        """
        Detect the language of an audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            Language code (e.g., "en", "es") or "unknown"
        """
        if not self.available:
            return "unknown"

        if not audio_path.exists():
            return "unknown"

        try:
            self._load_model()

            # Load audio and detect language
            audio = whisper.load_audio(str(audio_path))
            audio = whisper.pad_or_trim(audio)

            # Make log-Mel spectrogram
            mel = whisper.log_mel_spectrogram(audio).to(self.model.device)

            # Detect language
            _, probs = self.model.detect_language(mel)
            detected_language = max(probs, key=probs.get)

            _log("info", f"Detected language: {detected_language}")
            return detected_language

        except Exception as e:
            _log("error", f"Language detection failed: {e}")
            return "unknown"

    def is_available(self) -> bool:
        """Check if Whisper is available."""
        return self.available

    def get_model_info(self) -> dict:
        """Get information about the current model."""
        return {
            "model_name": self.model_name if self.available else None,
            "device": self.device if self.available else None,
            "loaded": self.model is not None,
            "available": self.available,
        }
