"""Helper to convert LLMService to CrewAI-compatible LLM."""

from crewai import LLM

from app.config import get_settings
from app.llm import LLMService
from app.tracing import get_tracer

logger = get_tracer()


def get_crewai_llm(llm_service: LLMService = None):
    """
    Get a CrewAI-compatible LLM object.
    
    CrewAI has its own LLM class that needs to be configured properly.
    This creates a CrewAI LLM instance for Ollama or OpenRouter.
    
    Args:
        llm_service: Optional LLMService instance (used for config reference).
    
    Returns:
        CrewAI LLM instance that works with CrewAI agents
    """
    import os
    settings = get_settings()
    
    if settings.llm_backend == "ollama":
        # CrewAI expects Ollama URL without /v1 suffix
        ollama_url = settings.ollama_base_url
        if ollama_url.endswith("/v1"):
            ollama_url = ollama_url[:-3]
        
        # Set environment variables that litellm might check
        os.environ["OLLAMA_API_BASE"] = ollama_url
        os.environ["OLLAMA_BASE_URL"] = ollama_url
        
        llm = LLM(
            model=f"ollama/{settings.ollama_model}",
            base_url=ollama_url,
            temperature=0.7,
        )
        
        logger.info(
            "CrewAI LLM created",
            extra={
                "backend": "ollama",
                "model": settings.ollama_model,
                "base_url": ollama_url
            }
        )
        return llm
    
    elif settings.llm_backend == "openrouter":
        llm = LLM(
            model=settings.openrouter_model,
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
            temperature=0.7,
        )
        
        logger.info(
            "CrewAI LLM created",
            extra={
                "backend": "openrouter",
                "model": settings.openrouter_model
            }
        )
        return llm
    
    else:
        raise ValueError(f"Unsupported LLM backend: {settings.llm_backend}")


def test_crewai_llm():
    """Test that CrewAI LLM works."""
    from crewai import Agent
    
    try:
        llm = get_crewai_llm()
        
        # Try to create an agent with it
        agent = Agent(
            role="Test Agent",
            goal="Test that LLM works",
            backstory="Test agent",
            llm=llm,
            verbose=False
        )
        
        logger.info("CrewAI LLM test successful - agent created!")
        return True
        
    except Exception as e:
        logger.error(f"CrewAI LLM test failed: {e}")
        return False


if __name__ == "__main__":
    # Test the helper
    print("Testing CrewAI LLM compatibility...")
    success = test_crewai_llm()
    if success:
        print("✅ SUCCESS! CrewAI LLM is compatible!")
    else:
        print("❌ FAILED! CrewAI LLM has issues.")
