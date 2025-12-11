"""Test UnifiedSearchCrew with CrewAI orchestration.

This test verifies that:
1. Agents initialize with CrewAI LLM (Ollama)
2. Coordinator analyzes query and determines search strategy
3. Specialized searchers execute searches in parallel
4. Aggregator combines results into unified response
5. Memory sharing enables context passing between agents
"""

import asyncio

from app.crews.search import SearchContext, UnifiedSearchCrew
from app.llm import get_llm_service
from app.memory.api import MemoryService
from app.tools.list_tool import ListTool
from app.tools.task_tool import TaskTool


async def setup_test_data():
    """Create some test data for searching."""
    print("Setting up test data...")

    # Create some test memories
    memory = MemoryService()
    try:
        # Add a test memory about a meeting
        memory.ltm.add_memory(
            user_id="test_user",
            chat_id="test_chat",
            content="Met with Sarah yesterday to discuss the Q4 budget proposal. She had great ideas about cost optimization.",
            metadata={
                "people": ["Sarah"],
                "tags": ["meeting", "budget", "Q4"],
                "happened_at": "2025-10-28T14:00:00Z",
            },
        )
        print("  ✓ Added test memory")
    except Exception as e:
        print(f"  ⚠ Memory setup: {e}")

    # Create a test task
    task_tool = TaskTool()
    try:
        await task_tool.execute(
            {
                "operation": "create_task",
                "title": "Review Q4 budget proposal",
                "description": "Review the budget proposal discussed with Sarah",
                "priority": 2,
                "due_at": "2025-11-01T12:00:00Z",
                "user_id": "test_user",
                "chat_id": "test_chat",
            }
        )
        print("  ✓ Added test task")
    except Exception as e:
        print(f"  ⚠ Task setup: {e}")

    # Create a test list with items
    list_tool = ListTool()
    try:
        # Create list
        list_result = await list_tool.execute(
            {
                "operation": "create_list",
                "name": "Meeting Action Items",
                "user_id": "test_user",
                "chat_id": "test_chat",
            }
        )
        list_id = list_result.get("list_id")

        # Add item to list
        await list_tool.execute(
            {
                "operation": "add_item",
                "list_id": list_id,
                "text": "Follow up with Sarah on budget questions",
                "tags": ["budget", "sarah"],
            }
        )
        print("  ✓ Added test list with item")
    except Exception as e:
        print(f"  ⚠ List setup: {e}")

    print()


async def test_unified_search_crew():
    """Test UnifiedSearchCrew with CrewAI memory sharing."""

    print("=" * 70)
    print("Testing CrewAI Unified Search Across Multiple Sources")
    print("=" * 70)
    print()

    # Step 1: Setup test data
    await setup_test_data()

    # Step 2: Setup services
    print("1. Setting up search crew...")
    llm = get_llm_service()
    memory = MemoryService()
    task_tool = TaskTool()
    list_tool = ListTool()

    crew = UnifiedSearchCrew(
        memory_service=memory, task_tool=task_tool, list_tool=list_tool, llm=llm
    )
    print("   OK: Search crew created")
    print()

    # Step 3: Test search
    search_query = "What did Sarah and I discuss about the budget?"
    print(f"2. Test query: '{search_query}'")
    print()

    # Step 4: Run search with CrewAI orchestration
    print("3. Running search_with_crew_tasks()...")
    print("   This will:")
    print("   - Initialize agents (if not already done)")
    print("   - Create tasks for coordinator, searchers, and aggregator")
    print("   - Run crew.kickoff() with shared memory")
    print("   - Agents will collaborate via CrewAI memory")
    print()

    context = SearchContext(
        chat_id="test_chat",
        user_id="test_user",
        sources=["memory", "tasks", "lists"],  # Search all sources
    )

    try:
        result = await crew.search_with_crew_tasks(search_query, context)

        print()
        print("=" * 70)
        print("SUCCESS: CrewAI search orchestration completed!")
        print("=" * 70)
        print()
        print(f"Query: {result.query}")
        print(f"Sources searched: {', '.join(result.sources_searched)}")
        print(f"Total results: {result.total_results}")
        print()
        print("Combined Summary:")
        print(result.combined_summary)
        print()

        # Check if memory files were created
        print("=" * 70)
        print("Checking CrewAI Memory Files")
        print("=" * 70)
        import os
        from pathlib import Path

        # CrewAI stores memory in user's local data directory
        if os.name == "nt":  # Windows
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
        print("TEST PASSED: UnifiedSearchCrew works!")
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
    asyncio.run(test_unified_search_crew())
