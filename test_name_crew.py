"""Quick test for name search through CrewAI."""
import sys
sys.path.insert(0, 'src')

from app.crews.search.crew import UnifiedSearchCrew
from app.memory import SearchContext

print("\n" + "=" * 80)
print("TESTING NAME SEARCH THROUGH CREWAI")
print("=" * 80)

crew = UnifiedSearchCrew()

# Simple name query
query = "como me llamo"
context = SearchContext()

import asyncio
result = asyncio.run(crew.search_with_crew_tasks(query, context))

print("\n" + "=" * 80)
print("RESULT:")
print("=" * 80)
print(result.summary)
