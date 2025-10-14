"""Pytest configuration and shared fixtures."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def test_data_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(autouse=True)
def test_env(test_data_dir, monkeypatch):
    """Set up test environment variables."""
    # Override settings for tests
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token_123")
    monkeypatch.setenv("LLM_BACKEND", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:3b")
    monkeypatch.setenv("VECTOR_BACKEND", "stub")
    monkeypatch.setenv("VECTOR_STORE_PATH", str(test_data_dir / "chroma"))
    monkeypatch.setenv("SQL_DB_PATH", str(test_data_dir / "test.sqlite"))
    monkeypatch.setenv("TRACE_FILE", str(test_data_dir / "trace.jsonl"))
    monkeypatch.setenv("TRACE_LEVEL", "debug")


@pytest.fixture
def sample_message():
    """Sample Telegram message for testing."""
    return {
        "message_id": 123,
        "chat": {"id": 456, "type": "private"},
        "from_user": {"id": 789, "username": "testuser"},
        "text": "Reunión con María mañana a las 10am",
        "date": 1697385600,
    }
