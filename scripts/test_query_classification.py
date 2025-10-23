"""Test intent classification for query vs note."""

import asyncio
from app.llm import LLMService
from app.agents.intent_classifier import IntentClassifier


async def test_query_classification():
    """Test that questions are classified as QUERY not NOTE."""
    llm = LLMService()
    classifier = IntentClassifier(llm)
    
    test_cases = [
        ("¿Qué guardé sobre María?", "query"),  # General memory query
        ("¿Qué hay en la lista?", "list"),  # List-specific query
        ("¿Cuáles son mis tareas?", "task"),  # Task-specific query
        ("What did I save about John?", "query"),  # General memory query
        ("Recuerda que a María le gusta el té", "note"),
        ("Añade leche a la lista", "list"),
        ("Recuérdame llamar a Juan", "task"),
        ("¿Qué sé de Barcelona?", "query"),  # General knowledge query
    ]
    
    print("Testing Intent Classification")
    print("=" * 60)
    
    for message, expected in test_cases:
        intent, confidence = await classifier.classify(message)
        status = "✅" if intent.value == expected else "❌"
        print(f"{status} '{message}'")
        print(f"   Expected: {expected}")
        print(f"   Got: {intent.value} (confidence: {confidence:.2f})")
        print()


if __name__ == "__main__":
    asyncio.run(test_query_classification())
