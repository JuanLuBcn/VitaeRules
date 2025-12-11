import asyncio
import os
import sys
from app.crews.search.crew import UnifiedSearchCrew, SearchContext
from app.memory.api import MemoryService

# Mock settings
os.environ["APP_ENV"] = "dev"
os.environ["CREWAI_VERBOSE_LEVEL"] = "2"
os.environ["CREWAI_LOG_LEVEL"] = "DEBUG"

async def test_search_crew():
    print("Initializing MemoryService...")
    memory_service = MemoryService()
    
    print("Initializing UnifiedSearchCrew...")
    search_crew = UnifiedSearchCrew(memory_service=memory_service)
    
    query = "Cuantos metros tiene el piso y cuando finalizaran las obras?"
    print(f"\nTesting search with query: '{query}'")
    
    context = SearchContext(
        chat_id="debug_chat",
        user_id="debug_user"
    )
    
    try:
        result = await search_crew.search_with_crew_tasks(query, context)
        print("\nSearch Result:")
        print(f"Query: {result.query}")
        print(f"Sources Searched: {result.sources_searched}")
        print(f"Total Results: {result.total_results}")
        print(f"Summary: {result.combined_summary}")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search_crew())
