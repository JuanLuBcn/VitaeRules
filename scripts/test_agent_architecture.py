"""
Test the new agent-based architecture end-to-end.

Tests each agent independently and the orchestrator integration.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from app.agents import (
    IntentClassifier,
    IntentType,
    ListAgent,
    NoteAgent,
    QueryAgent,
    TaskAgent,
)
from app.llm import LLMService
from app.memory import MemoryService


async def test_intent_classifier():
    """Test intent classification."""
    print("\n=== Testing IntentClassifier ===\n")
    
    llm = LLMService()
    classifier = IntentClassifier(llm)
    
    test_cases = [
        ("Añade mantequilla a la lista de la compra", IntentType.LIST),
        ("Remind me to call John tomorrow", IntentType.TASK),
        ("Remember that John likes coffee", IntentType.NOTE),
        ("What did I do yesterday?", IntentType.QUERY),
        ("Berenjenas, tomates y aguacates", IntentType.LIST),
        ("I need to finish the report by Friday", IntentType.TASK),
        ("Tell me about Barcelona", IntentType.QUERY),
    ]
    
    passed = 0
    for message, expected in test_cases:
        intent, confidence = await classifier.classify(message)
        status = "✅" if intent == expected else "❌"
        print(f"{status} '{message[:50]}'")
        print(f"   Expected: {expected.value}, Got: {intent.value} (confidence: {confidence:.2f})")
        if intent == expected:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(test_cases)}")
    return passed == len(test_cases)


async def test_list_agent():
    """Test list agent."""
    print("\n=== Testing ListAgent ===\n")
    
    llm = LLMService()
    memory = MemoryService()
    agent = ListAgent(llm, memory)
    
    # Test can_handle
    can_handle, confidence = await agent.can_handle("Añade mantequilla a la lista")
    print(f"Can handle list message: {can_handle} (confidence: {confidence:.2f})")
    
    # Test adding items
    print("\nTest: Add single item")
    result = await agent.handle(
        "Añade mantequilla a la lista de la compra",
        chat_id="test_chat",
        user_id="test_user",
    )
    print(f"Success: {result.success}")
    print(f"Needs confirmation: {result.needs_confirmation}")
    print(f"Preview: {result.preview}")
    
    # Test multiple items
    print("\nTest: Add multiple items")
    result = await agent.handle(
        "Berenjenas, tomates y aguacates",
        chat_id="test_chat",
        user_id="test_user",
    )
    print(f"Success: {result.success}")
    print(f"Preview: {result.preview}")
    
    # Test query
    print("\nTest: Query list")
    result = await agent.handle(
        "Qué hay en la lista de la compra?",
        chat_id="test_chat",
        user_id="test_user",
    )
    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    
    return True


async def test_task_agent():
    """Test task agent."""
    print("\n=== Testing TaskAgent ===\n")
    
    llm = LLMService()
    memory = MemoryService()
    agent = TaskAgent(llm, memory)
    
    # Test can_handle
    can_handle, confidence = await agent.can_handle("Remind me to call John")
    print(f"Can handle task message: {can_handle} (confidence: {confidence:.2f})")
    
    # Test creating task
    print("\nTest: Create task")
    result = await agent.handle(
        "Remind me to call John tomorrow",
        chat_id="test_chat",
        user_id="test_user",
    )
    print(f"Success: {result.success}")
    print(f"Needs confirmation: {result.needs_confirmation}")
    print(f"Preview: {result.preview}")
    
    # Test query tasks
    print("\nTest: Query tasks")
    result = await agent.handle(
        "What are my tasks?",
        chat_id="test_chat",
        user_id="test_user",
    )
    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    
    return True


async def test_note_agent():
    """Test note agent."""
    print("\n=== Testing NoteAgent ===\n")
    
    llm = LLMService()
    memory = MemoryService()
    agent = NoteAgent(llm, memory)
    
    # Test can_handle
    can_handle, confidence = await agent.can_handle("Remember that John likes coffee")
    print(f"Can handle note message: {can_handle} (confidence: {confidence:.2f})")
    
    # Test saving note
    print("\nTest: Save note")
    result = await agent.handle(
        "Remember that John likes coffee and tea",
        chat_id="test_chat",
        user_id="test_user",
    )
    print(f"Success: {result.success}")
    print(f"Needs confirmation: {result.needs_confirmation}")
    print(f"Preview: {result.preview}")
    
    return True


async def test_query_agent():
    """Test query agent."""
    print("\n=== Testing QueryAgent ===\n")
    
    llm = LLMService()
    memory = MemoryService()
    agent = QueryAgent(llm, memory)
    
    # Test can_handle
    can_handle, confidence = await agent.can_handle("What did I do yesterday?")
    print(f"Can handle query message: {can_handle} (confidence: {confidence:.2f})")
    
    # Test query
    print("\nTest: Ask question")
    result = await agent.handle(
        "Tell me about John",
        chat_id="test_chat",
        user_id="test_user",
    )
    print(f"Success: {result.success}")
    print(f"Message: {result.message[:200]}...")
    
    return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing New Agent-Based Architecture")
    print("=" * 60)
    
    try:
        # Test each component
        await test_intent_classifier()
        await test_list_agent()
        await test_task_agent()
        await test_note_agent()
        await test_query_agent()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
