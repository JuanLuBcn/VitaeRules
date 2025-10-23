"""Comprehensive test for all agents and tools initialization."""

import asyncio
from app.llm import LLMService
from app.memory import MemoryService as MemService
from app.agents.orchestrator import AgentOrchestrator
from app.agents import IntentType


async def test_all_agents():
    """Test that all agents are properly initialized with correct tools."""
    print("=" * 60)
    print("TESTING ALL AGENTS INITIALIZATION")
    print("=" * 60)
    
    # Initialize orchestrator
    llm = LLMService()
    memory = MemService()
    orchestrator = AgentOrchestrator(llm, memory)
    
    # Test 1: Check all agents exist
    print("\n✅ Test 1: Checking all agents exist...")
    expected_agents = [IntentType.LIST, IntentType.TASK, IntentType.NOTE, IntentType.QUERY]
    for intent_type in expected_agents:
        assert intent_type in orchestrator.agents, f"Missing agent for {intent_type}"
        print(f"   ✓ {intent_type.value} agent exists")
    
    # Test 2: Check ListAgent has ListTool
    print("\n✅ Test 2: Checking ListAgent initialization...")
    list_agent = orchestrator.agents[IntentType.LIST]
    assert hasattr(list_agent, 'list_tool'), "ListAgent missing list_tool"
    assert hasattr(list_agent.list_tool, 'execute'), "ListTool missing execute method"
    from app.tools.list_tool import ListTool
    assert isinstance(list_agent.list_tool, ListTool), "list_tool is not ListTool instance"
    print(f"   ✓ ListAgent.list_tool: {type(list_agent.list_tool).__name__}")
    print(f"   ✓ Has execute method: {hasattr(list_agent.list_tool, 'execute')}")
    
    # Test 3: Check TaskAgent has TaskTool
    print("\n✅ Test 3: Checking TaskAgent initialization...")
    task_agent = orchestrator.agents[IntentType.TASK]
    assert hasattr(task_agent, 'task_tool'), "TaskAgent missing task_tool"
    assert hasattr(task_agent.task_tool, 'execute'), "TaskTool missing execute method"
    from app.tools.task_tool import TaskTool
    assert isinstance(task_agent.task_tool, TaskTool), "task_tool is not TaskTool instance"
    print(f"   ✓ TaskAgent.task_tool: {type(task_agent.task_tool).__name__}")
    print(f"   ✓ Has execute method: {hasattr(task_agent.task_tool, 'execute')}")
    
    # Test 4: Check NoteAgent has MemoryService
    print("\n✅ Test 4: Checking NoteAgent initialization...")
    note_agent = orchestrator.agents[IntentType.NOTE]
    assert hasattr(note_agent, 'memory'), "NoteAgent missing memory service"
    assert hasattr(note_agent.memory, 'save_memory'), "MemoryService missing save_memory method"
    assert isinstance(note_agent.memory, MemService), "memory is not MemoryService instance"
    print(f"   ✓ NoteAgent.memory: {type(note_agent.memory).__name__}")
    print(f"   ✓ Has save_memory method: {hasattr(note_agent.memory, 'save_memory')}")
    
    # Test 5: Check QueryAgent has RetrievalCrew
    print("\n✅ Test 5: Checking QueryAgent initialization...")
    query_agent = orchestrator.agents[IntentType.QUERY]
    assert hasattr(query_agent, 'retrieval_crew'), "QueryAgent missing retrieval_crew"
    assert hasattr(query_agent.retrieval_crew, 'retrieve'), "RetrievalCrew missing retrieve method"
    from app.crews.retrieval import RetrievalCrew
    assert isinstance(query_agent.retrieval_crew, RetrievalCrew), "retrieval_crew is not RetrievalCrew instance"
    print(f"   ✓ QueryAgent.retrieval_crew: {type(query_agent.retrieval_crew).__name__}")
    print(f"   ✓ Has retrieve method: {hasattr(query_agent.retrieval_crew, 'retrieve')}")
    
    print("\n" + "=" * 60)
    print("TESTING AGENT FUNCTIONALITY")
    print("=" * 60)
    
    # Test 6: Test ListAgent with actual message
    print("\n✅ Test 6: Testing ListAgent with real message...")
    try:
        result = await orchestrator.handle_message(
            message="Añade pan y mantequilla a la lista de la compra",
            chat_id="test_123",
            user_id="test_user"
        )
        assert 'message' in result, "ListAgent result missing 'message'"
        assert result.get('needs_confirmation') is not None, "ListAgent result missing 'needs_confirmation'"
        print(f"   ✓ ListAgent responds correctly")
        print(f"   ✓ Response: {result['message'][:80]}...")
    except Exception as e:
        print(f"   ✗ ListAgent failed: {e}")
        raise
    
    # Test 7: Test TaskAgent with actual message
    print("\n✅ Test 7: Testing TaskAgent with real message...")
    try:
        result = await orchestrator.handle_message(
            message="Recuérdame llamar a Juan mañana",
            chat_id="test_456",
            user_id="test_user"
        )
        assert 'message' in result, "TaskAgent result missing 'message'"
        print(f"   ✓ TaskAgent responds correctly")
        print(f"   ✓ Response: {result['message'][:80]}...")
    except Exception as e:
        print(f"   ✗ TaskAgent failed: {e}")
        raise
    
    # Test 8: Test NoteAgent with actual message
    print("\n✅ Test 8: Testing NoteAgent with real message...")
    try:
        result = await orchestrator.handle_message(
            message="Recuerda que a María le gusta el té verde",
            chat_id="test_789",
            user_id="test_user"
        )
        assert 'message' in result, "NoteAgent result missing 'message'"
        print(f"   ✓ NoteAgent responds correctly")
        print(f"   ✓ Response: {result['message'][:80]}...")
    except Exception as e:
        print(f"   ✗ NoteAgent failed: {e}")
        raise
    
    # Test 9: Test QueryAgent with actual message
    print("\n✅ Test 9: Testing QueryAgent with real message...")
    try:
        result = await orchestrator.handle_message(
            message="¿Qué guardé sobre María?",
            chat_id="test_101",
            user_id="test_user"
        )
        assert 'message' in result, "QueryAgent result missing 'message'"
        print(f"   ✓ QueryAgent responds correctly")
        print(f"   ✓ Response: {result['message'][:80]}...")
    except Exception as e:
        print(f"   ✗ QueryAgent failed: {e}")
        raise
    
    # Test 10: Test async methods are correctly awaited
    print("\n✅ Test 10: Testing async/await correctness...")
    list_tool = list_agent.list_tool
    task_tool = task_agent.task_tool
    
    # ListTool.execute should be async
    import inspect
    assert inspect.iscoroutinefunction(list_tool.execute), "ListTool.execute should be async"
    print(f"   ✓ ListTool.execute is async (correct)")
    
    # TaskTool.execute should be async
    assert inspect.iscoroutinefunction(task_tool.execute), "TaskTool.execute should be async"
    print(f"   ✓ TaskTool.execute is async (correct)")
    
    # MemoryService.save_memory should NOT be async
    assert not inspect.iscoroutinefunction(note_agent.memory.save_memory), "MemoryService.save_memory should NOT be async"
    print(f"   ✓ MemoryService.save_memory is sync (correct)")
    
    # RetrievalCrew.retrieve should NOT be async
    assert not inspect.iscoroutinefunction(query_agent.retrieval_crew.retrieve), "RetrievalCrew.retrieve should NOT be async"
    print(f"   ✓ RetrievalCrew.retrieve is sync (correct)")
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! ✅")
    print("=" * 60)
    print("\nSummary:")
    print("  ✓ All 4 agents properly initialized")
    print("  ✓ All tools/services have correct types")
    print("  ✓ All required methods exist")
    print("  ✓ All agents respond to messages")
    print("  ✓ Async/await usage is correct")
    print("\n✅ System is ready for production!")


if __name__ == "__main__":
    asyncio.run(test_all_agents())
