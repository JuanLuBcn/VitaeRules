"""LLM service for conversational AI and intent detection."""

import json
import re
from typing import Any

from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.tracing import get_tracer

logger = get_tracer()


class LLMService:
    """Service for LLM interactions."""

    def __init__(self):
        """Initialize LLM service."""
        self.settings = get_settings()
        
        # Initialize LLM based on backend
        if self.settings.llm_backend == "ollama":
            # Ollama uses OpenAI-compatible API at /v1 endpoint
            ollama_url = self.settings.ollama_base_url
            if not ollama_url.endswith("/v1"):
                ollama_url = f"{ollama_url}/v1"
            
            self.llm = ChatOpenAI(
                base_url=ollama_url,
                model=self.settings.ollama_model,
                temperature=0.7,
                api_key="ollama",  # Dummy key for Ollama (doesn't use authentication)
            )
            logger.info(
                "LLM initialized",
                extra={
                    "backend": "ollama",
                    "model": self.settings.ollama_model,
                    "base_url": ollama_url,
                },
            )
        elif self.settings.llm_backend == "openrouter":
            self.llm = ChatOpenAI(
                base_url=self.settings.openrouter_base_url,
                api_key=self.settings.openrouter_api_key,
                model=self.settings.openrouter_model,
                temperature=0.7,
            )
            logger.info(
                "LLM initialized", extra={"backend": "openrouter", "model": self.settings.openrouter_model}
            )
        else:
            raise ValueError(f"Unsupported LLM backend: {self.settings.llm_backend}")

    def chat(self, messages: list[dict[str, str]]) -> str:
        """
        Send chat messages to LLM and get response.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            LLM response text
        """
        try:
            response = self.llm.invoke(messages)
            return response.content
        except Exception as e:
            logger.error(f"LLM chat error: {e}")
            raise

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """
        Generate text from a prompt.

        Args:
            prompt: User prompt
            system_prompt: Optional system message

        Returns:
            Generated text
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return self.chat(messages)

    def generate_json(self, prompt: str, system_prompt: str | None = None) -> dict[str, Any]:
        """
        Generate structured JSON output.

        Args:
            prompt: User prompt
            system_prompt: Optional system message

        Returns:
            Parsed JSON response
        """
        full_system = (system_prompt or "") + "\n\nRespond ONLY with valid JSON. No other text."
        response = self.generate(prompt, full_system)

        # Try to extract JSON from response
        try:
            # Look for JSON in code blocks
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            # Remove JSON comments (// style)
            json_str = re.sub(r'//.*?(?=\n|$)', '', json_str)
            # Remove multi-line comments (/* */ style)
            json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)
            # Remove trailing commas before closing braces/brackets
            json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)

            return json.loads(json_str)
        except (json.JSONDecodeError, IndexError) as e:
            logger.error(f"Failed to parse JSON from LLM: {e}")
            logger.error(f"Response was: {response}")
            raise ValueError(f"LLM did not return valid JSON: {response[:200]}")


# Singleton instance
_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """Get or create LLM service singleton."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
