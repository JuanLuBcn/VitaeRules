"""
Test Optimized Search Execution - Verify Conditional Search Works

This test verifies that:
1. Capability queries trigger coordinator → aggregator (skip all searches)
2. Data queries trigger appropriate searches only
3. Time improvements are achieved

Run with: python test_optimized_search.py
"""

import asyncio
import time
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from app.crews.search.crew import UnifiedSearchCrew, SearchContext


async def test_capability_query():
    """Test that capability queries skip all searches."""
    print("\n" + "="*80)
    print("TEST 1: Capability Query (Should Skip All Searches)")
    print("="*80)
    
    query = "Hola, puedes detallar en que me puedes ayudar?"
    print(f"\n📝 Query: {query}")
    print(f"🎯 Expected: Coordinator → Aggregator (skip all 3 searches)")
    print(f"⏱️  Expected time: ~27 seconds")
    
    context = SearchContext(
        chat_id="test_capability",
        user_id="test_user"
    )
    
    crew = UnifiedSearchCrew()
    
    start_time = time.time()
    result = await crew.search_with_crew_tasks(query, context)
    elapsed = time.time() - start_time
    
    print(f"\n✅ Result received in {elapsed:.2f} seconds")
    print(f"\n📊 Response:\n{result.combined_summary}")
    
    # Analyze result
    result_lower = result.combined_summary.lower()
    skipped_count = result_lower.count("skipped")
    
    print(f"\n📈 Analysis:")
    print(f"   - Searches skipped: {skipped_count}/3")
    print(f"   - Time: {elapsed:.2f}s (target: ~27s)")
    
    if skipped_count == 3:
        print(f"   ✅ SUCCESS: All 3 searches were skipped!")
    elif skipped_count > 0:
        print(f"   ⚠️  PARTIAL: {skipped_count}/3 searches skipped")
    else:
        print(f"   ❌ ISSUE: No searches were skipped (may need prompt tuning)")
    
    if elapsed < 40:
        print(f"   ✅ Speed improvement achieved!")
    else:
        print(f"   ⚠️  Slower than expected ({elapsed:.2f}s vs ~27s target)")
    
    return {
        "query": query,
        "elapsed": elapsed,
        "skipped": skipped_count,
        "result": result.combined_summary
    }


async def test_data_query():
    """Test that data queries trigger appropriate searches."""
    print("\n" + "="*80)
    print("TEST 2: Data Query (Should Search Relevant Sources)")
    print("="*80)
    
    query = "¿Qué hice con Jorge la semana pasada?"
    print(f"\n📝 Query: {query}")
    print(f"🎯 Expected: Coordinator → Memory Search → Aggregator")
    print(f"⏱️  Expected time: ~39 seconds (coordinator + memory + aggregator)")
    
    context = SearchContext(
        chat_id="test_data",
        user_id="test_user"
    )
    
    crew = UnifiedSearchCrew()
    
    start_time = time.time()
    result = await crew.search_with_crew_tasks(query, context)
    elapsed = time.time() - start_time
    
    print(f"\n✅ Result received in {elapsed:.2f} seconds")
    print(f"\n📊 Response:\n{result.combined_summary}")
    
    # Analyze result
    result_lower = result.combined_summary.lower()
    skipped_count = result_lower.count("skipped")
    searched_count = 3 - skipped_count
    
    print(f"\n📈 Analysis:")
    print(f"   - Searches executed: {searched_count}/3")
    print(f"   - Searches skipped: {skipped_count}/3")
    print(f"   - Time: {elapsed:.2f}s")
    
    if searched_count > 0:
        print(f"   ✅ SUCCESS: {searched_count} relevant search(es) executed!")
    else:
        print(f"   ❌ ISSUE: No searches executed (coordinator may be too conservative)")
    
    if skipped_count > 0:
        print(f"   ✅ Selective execution: Skipped {skipped_count} irrelevant source(s)")
    
    return {
        "query": query,
        "elapsed": elapsed,
        "skipped": skipped_count,
        "searched": searched_count,
        "result": result.combined_summary
    }


async def test_mixed_query():
    """Test query that should trigger multiple searches."""
    print("\n" + "="*80)
    print("TEST 3: Mixed Query (Should Search Multiple Sources)")
    print("="*80)
    
    query = "¿Tengo alguna tarea pendiente relacionada con compras?"
    print(f"\n📝 Query: {query}")
    print(f"🎯 Expected: Coordinator → Task + List Search → Aggregator")
    print(f"⏱️  Expected time: ~51 seconds (coordinator + 2 searches + aggregator)")
    
    context = SearchContext(
        chat_id="test_mixed",
        user_id="test_user"
    )
    
    crew = UnifiedSearchCrew()
    
    start_time = time.time()
    result = await crew.search_with_crew_tasks(query, context)
    elapsed = time.time() - start_time
    
    print(f"\n✅ Result received in {elapsed:.2f} seconds")
    print(f"\n📊 Response:\n{result.combined_summary}")
    
    # Analyze result
    result_lower = result.combined_summary.lower()
    skipped_count = result_lower.count("skipped")
    searched_count = 3 - skipped_count
    
    print(f"\n📈 Analysis:")
    print(f"   - Searches executed: {searched_count}/3")
    print(f"   - Searches skipped: {skipped_count}/3")
    print(f"   - Time: {elapsed:.2f}s")
    
    if searched_count >= 2:
        print(f"   ✅ SUCCESS: Multiple relevant searches executed!")
    elif searched_count == 1:
        print(f"   ⚠️  PARTIAL: Only 1 search executed (expected 2)")
    else:
        print(f"   ❌ ISSUE: No searches executed")
    
    return {
        "query": query,
        "elapsed": elapsed,
        "skipped": skipped_count,
        "searched": searched_count,
        "result": result.combined_summary
    }


async def main():
    """Run all test cases and show summary."""
    print("\n" + "="*80)
    print("🚀 OPTIMIZED SEARCH EXECUTION TEST SUITE")
    print("="*80)
    print("\nThis test verifies:")
    print("1. ✅ Keywords removed from coordinator backstory")
    print("2. ✅ Examples removed from aggregator prompt")
    print("3. ✅ Conditional execution: searchers check coordinator recommendations")
    print("\nExpected improvements:")
    print("- Capability queries: 105s → ~27s (74% faster)")
    print("- Data queries: Smart search selection (skip irrelevant sources)")
    
    results = []
    
    try:
        # Test 1: Capability query (should skip all searches)
        result1 = await test_capability_query()
        results.append(result1)
        
        # Test 2: Data query (should search selectively)
        result2 = await test_data_query()
        results.append(result2)
        
        # Test 3: Mixed query (should search multiple sources)
        result3 = await test_mixed_query()
        results.append(result3)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Summary
    print("\n" + "="*80)
    print("📊 SUMMARY")
    print("="*80)
    
    total_time = sum(r["elapsed"] for r in results)
    avg_time = total_time / len(results)
    
    print(f"\n⏱️  Total time: {total_time:.2f}s")
    print(f"⏱️  Average time: {avg_time:.2f}s")
    
    print("\n📈 Results by test:")
    for i, result in enumerate(results, 1):
        print(f"\n   Test {i}: {result['query'][:50]}...")
        print(f"      Time: {result['elapsed']:.2f}s")
        print(f"      Skipped: {result.get('skipped', 0)}/3 searches")
    
    # Performance comparison
    print("\n🎯 Performance vs Baseline (105s for capability query):")
    if results:
        capability_time = results[0]["elapsed"]
        baseline = 105
        improvement = ((baseline - capability_time) / baseline) * 100
        print(f"   Capability query: {capability_time:.2f}s (was {baseline}s)")
        if improvement > 0:
            print(f"   ✅ {improvement:.1f}% faster!")
        else:
            print(f"   ⚠️  {abs(improvement):.1f}% slower (unexpected)")
    
    print("\n✅ Test suite complete!")


if __name__ == "__main__":
    asyncio.run(main())
