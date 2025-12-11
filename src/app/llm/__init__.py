"""LLM integration for VitaeRules."""

from app.llm.service import LLMService, get_llm_service
from app.llm.crewai_llm import get_crewai_llm

__all__ = ["LLMService", "get_llm_service", "get_crewai_llm"]
