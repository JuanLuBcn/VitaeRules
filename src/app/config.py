"""Application configuration using pydantic-settings."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    app_env: Literal["dev", "test", "prod"] = Field(default="dev", alias="APP_ENV")

    # Telegram
    telegram_bot_token: str = Field(..., alias="TELEGRAM_BOT_TOKEN")

    # LLM Configuration
    llm_backend: Literal["ollama", "openrouter"] = Field(default="ollama", alias="LLM_BACKEND")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="qwen3:1.7b", alias="OLLAMA_MODEL")
    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(default="anthropic/claude-3.5-sonnet", alias="OPENROUTER_MODEL")

    # Memory & Storage
    vector_backend: Literal["chroma", "stub"] = Field(default="chroma", alias="VECTOR_BACKEND")
    vector_store_path: Path = Field(default=Path("data/chroma"), alias="VECTOR_STORE_PATH")
    sql_db_path: Path = Field(default=Path("data/app.sqlite"), alias="SQL_DB_PATH")
    storage_path: Path = Field(default=Path("data/storage"), alias="STORAGE_PATH")

    # Tracing & Logging
    trace_level: Literal["debug", "info", "warning", "error"] = Field(
        default="info", alias="TRACE_LEVEL"
    )
    trace_file: Path = Field(default=Path("data/trace.jsonl"), alias="TRACE_FILE")

    # Application Settings
    approval_timeout_minutes: int = Field(default=10, alias="APPROVAL_TIMEOUT_MINUTES")
    max_clarify_questions: int = Field(default=3, alias="MAX_CLARIFY_QUESTIONS")
    zero_evidence_policy: Literal["strict", "allow"] = Field(
        default="strict", alias="ZERO_EVIDENCE_POLICY"
    )
    default_timezone: str = Field(default="Europe/Madrid", alias="DEFAULT_TIMEZONE")

    # Retrieval Settings
    retrieval_top_k: int = Field(default=4, alias="RETRIEVAL_TOP_K")
    enable_hybrid_search: bool = Field(default=True, alias="ENABLE_HYBRID_SEARCH")

    # STT (Speech-to-Text)
    stt_model: str = Field(default="base", alias="STT_MODEL")
    stt_language: str = Field(default="es", alias="STT_LANGUAGE")
    stt_device: Literal["cpu", "cuda"] = Field(default="cpu", alias="STT_DEVICE")

    # Feature Flags
    enable_voice: bool = Field(default=True, alias="ENABLE_VOICE")
    enable_diary: bool = Field(default=False, alias="ENABLE_DIARY")

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.vector_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.sql_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.trace_file.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.mkdir(parents=True, exist_ok=True)


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.ensure_directories()
    return _settings


def reload_settings() -> Settings:
    """Reload settings (useful for testing)."""
    global _settings
    _settings = Settings()
    _settings.ensure_directories()
    return _settings
