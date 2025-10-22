"""
Test semantic search to verify it filters memories by relevance.

This script:
1. Adds 3 diverse memories (pizza, Python programming, car repair)
2. Queries for "programming"
3. Verifies only the Python memory is returned (semantic filtering works)
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from app.memory import MemoryItem, MemoryQuery, MemorySection, MemoryService, MemorySource


def main():
    """Test semantic search with diverse memories."""
    print("=" * 70)
    print("SEMANTIC SEARCH TEST")
    print("=" * 70)

    # Initialize memory service
    from app.memory.long_term import LongTermMemory
    from app.memory.short_term import ShortTermMemory

    store_path = project_root / "data" / "chroma_test_semantic"
    ltm = LongTermMemory(store_path=store_path)
    stm = ShortTermMemory()
    mem = MemoryService(stm=stm, ltm=ltm)

    # Show current state
    print(f"\n📊 Initial state:")
    print(f"   Total memories: {mem.ltm.count(None)}")

    # Add 3 diverse memories
    print(f"\n➕ Adding 3 diverse memories...")

    memories = [
        MemoryItem(
            title="Pizza Lunch",
            content="Had delicious pizza for lunch with friends at Italian restaurant. "
            "Ordered margherita and pepperoni. The crust was perfect and crispy.",
            source=MemorySource.CAPTURE,
            section=MemorySection.NOTE,
            tags=["food", "lunch", "social"],
            chat_id="test_chat",
            user_id="test_user",
        ),
        MemoryItem(
            title="Python Code Review",
            content="Had team meeting to review Python code. Discussed best practices, "
            "type hints, async/await patterns, and testing strategies. Refactored "
            "the authentication module using proper OOP design.",
            source=MemorySource.CAPTURE,
            section=MemorySection.NOTE,
            tags=["programming", "python", "work"],
            chat_id="test_chat",
            user_id="test_user",
        ),
        MemoryItem(
            title="Car Maintenance",
            content="Took car to mechanic for regular maintenance. Got oil change, "
            "tire rotation, and brake inspection. Everything looks good for "
            "another 5000 miles.",
            source=MemorySource.CAPTURE,
            section=MemorySection.NOTE,
            tags=["car", "maintenance"],
            chat_id="test_chat",
            user_id="test_user",
        ),
    ]

    for memory in memories:
        mem.ltm.add(memory)
        print(f"   ✓ Added: {memory.title}")

    # Show updated state
    print(f"\n📊 After adding:")
    print(f"   Total memories: {mem.ltm.count(None)}")

    # Test 1: Search for programming
    print(f"\n" + "=" * 70)
    print("TEST 1: Search for 'programming'")
    print("=" * 70)

    query = MemoryQuery(
        query="Tell me about programming and code reviews",
        top_k=10,
    )

    results = mem.ltm.search(query)

    print(f"\n🔍 Query: '{query.query}'")
    print(f"📊 Results: {len(results)} memories found")
    print()

    for i, result in enumerate(results, 1):
        print(f"{i}. {result.item.title}")
        print(f"   Score: {result.score:.4f}")
        print(f"   Content preview: {result.item.content[:80]}...")
        print()

    # Analyze results
    print("=" * 70)
    print("ANALYSIS")
    print("=" * 70)

    if len(results) == 0:
        print("❌ FAIL: No results returned")
    elif len(results) == 1:
        if "Python" in results[0].item.title:
            print("✅ PASS: Only the Python memory returned (perfect semantic filtering)")
        else:
            print(f"❌ FAIL: Wrong memory returned: {results[0].item.title}")
    elif len(results) == 3:
        # Check if Python is ranked highest
        if "Python" in results[0].item.title:
            print("⚠️  PARTIAL: All 3 memories returned, but Python ranked highest")
            print("    This suggests semantic search is working but not filtering aggressively")
        else:
            print("❌ FAIL: All memories returned and Python not ranked highest")
            print("    This suggests semantic search may not be working properly")
    else:
        print(f"⚠️  UNEXPECTED: {len(results)} results (expected 1 or 3)")

    # Test 2: Search for food
    print(f"\n" + "=" * 70)
    print("TEST 2: Search for 'food and restaurants'")
    print("=" * 70)

    query2 = MemoryQuery(
        query="What did I eat at restaurants recently?",
        top_k=10,
    )

    results2 = mem.ltm.search(query2)

    print(f"\n🔍 Query: '{query2.query}'")
    print(f"📊 Results: {len(results2)} memories found")
    print()

    for i, result in enumerate(results2, 1):
        print(f"{i}. {result.item.title}")
        print(f"   Score: {result.score:.4f}")
        print(f"   Content preview: {result.item.content[:80]}...")
        print()

    if len(results2) >= 1 and "Pizza" in results2[0].item.title:
        print("✅ Pizza memory ranked highest for food query")
    else:
        print("⚠️  Pizza memory not ranked highest for food query")

    # Test 3: Search for cars
    print(f"\n" + "=" * 70)
    print("TEST 3: Search for 'vehicle maintenance'")
    print("=" * 70)

    query3 = MemoryQuery(
        query="When did I last service my vehicle?",
        top_k=10,
    )

    results3 = mem.ltm.search(query3)

    print(f"\n🔍 Query: '{query3.query}'")
    print(f"📊 Results: {len(results3)} memories found")
    print()

    for i, result in enumerate(results3, 1):
        print(f"{i}. {result.item.title}")
        print(f"   Score: {result.score:.4f}")
        print(f"   Content preview: {result.item.content[:80]}...")
        print()

    if len(results3) >= 1 and "Car" in results3[0].item.title:
        print("✅ Car memory ranked highest for vehicle query")
    else:
        print("⚠️  Car memory not ranked highest for vehicle query")

    # Final summary
    print(f"\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    print("Semantic search IS using Chroma's vector similarity search.")
    print("The question is: Does it filter aggressively or return all with ranking?")
    print()
    print("Expected behavior:")
    print("  - Query 'programming' → Only Python memory (score filtering)")
    print("  - OR all 3 memories with Python ranked highest (ranking only)")
    print()
    print("Check the results above to determine which behavior you're seeing.")
    print()


if __name__ == "__main__":
    main()
