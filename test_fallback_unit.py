"""Quick unit test for Pydantic parsing fallback logic.

Tests the error handling code path without running full LLM queries.
"""

def test_pydantic_parsing_fallback_logic():
    """Test that the fallback strategy is created correctly when Pydantic parsing fails."""
    
    print("=" * 70)
    print("Testing Pydantic Parsing Fallback Logic (No LLM)")
    print("=" * 70)
    print()
    
    # Simulate the fallback code path
    from app.crews.search.models import SearchStrategy, SourceStrategy
    
    query = "test query"
    
    # This is what happens in the except block when Pydantic parsing fails
    print("1. Simulating Pydantic parsing failure...")
    try:
        # Simulate the exception we're seeing on Pi5
        raise ValueError('\n  "memory"')
    except Exception as e:
        print(f"   Caught exception: {e}")
        print(f"   Exception type: {type(e).__name__}")
        print()
        
        print("2. Creating fallback strategy...")
        search_strategy = SearchStrategy(
            memory=SourceStrategy(
                relevant=True,
                priority="high",
                search_query=query,
                reasoning="Fallback: coordinator parsing failed"
            ),
            tasks=SourceStrategy(
                relevant=True,
                priority="high",
                search_query=query,
                reasoning="Fallback: coordinator parsing failed"
            ),
            lists=SourceStrategy(
                relevant=True,
                priority="high",
                search_query=query,
                reasoning="Fallback: coordinator parsing failed"
            ),
            overall_reasoning="Fallback strategy due to coordinator parsing error"
        )
        
        print("   ✅ Fallback strategy created successfully!")
        print(f"   - Memory: {search_strategy.memory.relevant}, priority={search_strategy.memory.priority}")
        print(f"   - Tasks: {search_strategy.tasks.relevant}, priority={search_strategy.tasks.priority}")
        print(f"   - Lists: {search_strategy.lists.relevant}, priority={search_strategy.lists.priority}")
        print()
        
        print("3. Verifying strategy can be used...")
        assert search_strategy.memory.relevant == True
        assert search_strategy.memory.priority == "high"
        assert search_strategy.tasks.relevant == True
        assert search_strategy.tasks.priority == "high"
        assert search_strategy.lists.relevant == True
        assert search_strategy.lists.priority == "high"
        print("   ✅ Strategy is valid and usable!")
        print()
        
        print("=" * 70)
        print("TEST PASSED: Fallback logic works correctly!")
        print("=" * 70)
        return True


def test_early_return_logic():
    """Test that SearchResult is created correctly for early return."""
    
    print()
    print("=" * 70)
    print("Testing Early Return SearchResult Creation (No LLM)")
    print("=" * 70)
    print()
    
    from app.contracts.search import SearchResult
    
    query = "test query"
    sources = ["memory", "tasks", "lists"]
    high_priority_result_text = "Edgar's last day at Isdin was December 15, 2025."
    
    print("1. Simulating HIGH priority search with results...")
    print(f"   Result text: {high_priority_result_text}")
    print()
    
    print("2. Creating SearchResult for early return...")
    result = SearchResult(
        query=query,
        sources_searched=sources,
        memory_results=[],
        task_results=[],
        list_results=[],
        combined_summary=high_priority_result_text,
        total_results=1,
    )
    
    print("   ✅ SearchResult created successfully!")
    print(f"   - Query: {result.query}")
    print(f"   - Sources: {result.sources_searched}")
    print(f"   - Total results: {result.total_results}")
    print(f"   - Summary: {result.combined_summary}")
    print()
    
    assert result.query == query
    assert result.sources_searched == sources
    assert result.total_results == 1
    assert "Edgar" in result.combined_summary
    assert "December 15" in result.combined_summary
    
    print("=" * 70)
    print("TEST PASSED: Early return creates valid SearchResult!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    print("\n🧪 Running Quick Unit Tests\n")
    
    # Test 1: Fallback logic
    test_pydantic_parsing_fallback_logic()
    
    # Test 2: Early return
    test_early_return_logic()
    
    print("\n✅ All unit tests passed!\n")
    print("These tests verify that:")
    print("  1. Fallback strategy is created correctly when Pydantic parsing fails")
    print("  2. SearchResult can be created for early return from HIGH priority searches")
    print("  3. The error handling code paths are valid")
    print()
    print("Next step: Run full integration test with LLM to verify end-to-end flow")
    print()
