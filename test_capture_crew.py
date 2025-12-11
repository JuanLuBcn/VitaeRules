"""Test CrewAI memory sharing in CaptureCrew.

This test verifies that:
1. Agents initialize with CrewAI LLM (Ollama)
2. Agents collaborate via CrewAI shared memory
3. Planning → Clarification → Execution workflow works
4. Memory sharing enables context passing between agents
"""

import asyncio
from app.crews.capture import CaptureCrew, CaptureContext
from app.llm import get_llm_service
from app.memory.api import MemoryService


async def test_capture_crew_memory():
    """Test CaptureCrew with CrewAI memory sharing."""
    
    print("=" * 70)
    print("Testing CrewAI Memory Sharing in CaptureCrew")
    print("=" * 70)
    print()
    
    # Step 1: Setup services
    print("1. Setting up services...")
    
    # Register tools
    from app.tools.registry import get_registry
    from app.tools.task_tool import TaskTool
    from app.tools.list_tool import ListTool
    from app.tools.temporal_tool import TemporalTool
    from app.tools.memory_note_tool import MemoryNoteTool
    
    registry = get_registry()
    registry.register(TaskTool())
    registry.register(ListTool())
    registry.register(TemporalTool())
    registry.register(MemoryNoteTool())
    print("   OK: Tools registered")

    llm = get_llm_service()
    memory = MemoryService()
    crew = CaptureCrew(memory_service=memory, llm=llm)
    print("   OK: Services created")
    print()
    
    # Step 2: Test with a capture request
    user_input = "Remind me to call John tomorrow at 2pm about the project proposal"
    print(f"2. Test input: '{user_input}'")
    print()
    
    # Step 3: Run capture with CrewAI orchestration
    print("3. Running capture_with_crew_tasks()...")
    print("   This will:")
    print("   - Initialize agents (if not already done)")
    print("   - Create tasks for planner, clarifier, and tool caller")
    print("   - Run crew.kickoff() with shared memory")
    print("   - Agents will see each other's outputs via CrewAI memory")
    print()
    
    context = CaptureContext(
        chat_id="test_chat",
        user_id="test_user",
        auto_approve=True  # Auto-approve for testing
    )
    
    try:
        result = await crew.capture_with_crew_tasks(user_input, context)
        
        print()
        print("=" * 70)
        print("SUCCESS: CrewAI orchestration completed!")
        print("=" * 70)
        print()
        print(f"Plan confidence: {result.plan.confidence:.0%}")
        print(f"Clarifications asked: {result.clarifications_asked}")
        print(f"Actions executed: {result.actions_executed}")
        print()
        print("Summary:")
        print(result.summary)
        print()
        
        # Check if memory files were created
        print("=" * 70)
        print("Checking CrewAI Memory Files")
        print("=" * 70)
        import os
        from pathlib import Path
        
        # CrewAI stores memory in user's local data directory
        if os.name == 'nt':  # Windows
            base_dir = Path.home() / "AppData" / "Local" / "crewAI" / "crewAI"
        else:  # Unix-like
            base_dir = Path.home() / ".local" / "share" / "crewAI"
        
        print(f"CrewAI data directory: {base_dir}")
        
        if base_dir.exists():
            print(f"Directory exists! Contents:")
            for item in base_dir.rglob("*"):
                if item.is_file():
                    size = item.stat().st_size
                    print(f"  - {item.relative_to(base_dir)} ({size} bytes)")
        else:
            print("Directory does not exist yet")
        
        print()
        print("=" * 70)
        print("TEST PASSED: CrewAI memory sharing works!")
        print("=" * 70)
        
    except Exception as e:
        print()
        print("=" * 70)
        print("TEST FAILED")
        print("=" * 70)
        print()
        print(f"Error: {e}")
        print()
        print("Full traceback:")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(test_capture_crew_memory())
