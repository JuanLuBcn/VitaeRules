"""Simple test to verify conditional execution actually works"""
import asyncio
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from app.crews.search.crew import UnifiedSearchCrew, SearchContext


async def main():
    print("\n" + "="*80)
    print("CONDITIONAL EXECUTION TEST")
    print("="*80)
    
    # Test with a shopping query - should skip Memory (tertiary)
    query = "¿Tengo alguna tarea pendiente relacionada con compras?"
    print(f"\n📝 Query: {query}")
    print(f"🎯 Expected: Tasks=PRIMARY, Lists=SECONDARY, Memory=TERTIARY (skip)\n")
    
    context = SearchContext(
        chat_id="test_conditional",
        user_id="test_user"
    )
    
    crew = UnifiedSearchCrew()
    result = await crew.search_with_crew_tasks(query, context)
    
    print(f"\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"\nResponse: {result.combined_summary[:200]}...")
    
    # The logs should show:
    # - "Coordinator analysis: ..." (what it decided)
    # - "DEBUG - Coordinator lowercase output: ..."
    # - "DEBUG - Memory initial match: ..."
    # - "DEBUG - Memory final decision: ..."
    # - "Conditional execution: Memory=?, Tasks=?, Lists=?"
    # - "Skipping memory search" OR "Adding memory search task"
    # - "Executing X tasks total (Y searches)"
    
    print(f"\n✅ Check the logs above to see:")
    print(f"   1. What the coordinator said about each source")
    print(f"   2. Whether parsing detected TERTIARY for Memory")
    print(f"   3. Final decision for each source (True/False)")
    print(f"   4. Which tasks were actually added to execution")
    print(f"   5. Which agent names appear in the execution logs")


if __name__ == "__main__":
    asyncio.run(main())
