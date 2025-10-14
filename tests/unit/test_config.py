"""Tests for configuration module."""

from pathlib import Path

from app.config import Settings, get_settings, reload_settings


def test_settings_from_env(test_env):
    """Test that settings load correctly from environment."""
    settings = reload_settings()

    assert settings.app_env == "test"
    assert settings.telegram_bot_token == "test_token_123"
    assert settings.llm_backend == "ollama"
    assert settings.ollama_model == "llama3.2:3b"
    assert settings.vector_backend == "stub"


def test_settings_defaults():
    """Test that settings have sensible defaults."""
    settings = Settings(telegram_bot_token="test")

    assert settings.approval_timeout_minutes == 10
    assert settings.max_clarify_questions == 3
    assert settings.zero_evidence_policy == "strict"
    assert settings.default_timezone == "Europe/Madrid"
    assert settings.retrieval_top_k == 4
    assert settings.enable_hybrid_search is True


def test_settings_paths(test_env, test_data_dir):
    """Test that path settings are Path objects."""
    settings = reload_settings()

    assert isinstance(settings.vector_store_path, Path)
    assert isinstance(settings.sql_db_path, Path)
    assert isinstance(settings.trace_file, Path)


def test_ensure_directories(test_env, test_data_dir):
    """Test that directories are created."""
    settings = reload_settings()
    settings.ensure_directories()

    assert settings.vector_store_path.parent.exists()
    assert settings.sql_db_path.parent.exists()
    assert settings.trace_file.parent.exists()


def test_get_settings_singleton():
    """Test that get_settings returns the same instance."""
    settings1 = get_settings()
    settings2 = get_settings()

    assert settings1 is settings2
