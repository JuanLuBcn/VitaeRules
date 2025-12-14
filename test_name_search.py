"""Test memory search for user's name."""
import sys
sys.path.insert(0, 'src')

from app.memory.api import MemoryService
from app.memory.schemas import MemoryQuery

print("\n" + "=" * 80)
print("TESTING NAME SEARCH")
print("=" * 80)

# Initialize service
memory_service = MemoryService()

# Test search for name
queries = [
    "nombre del usuario",
    "como me llamo",
    "user name",
    "JuanLu"
]

for query_text in queries:
    print(f"\n🔍 Query: '{query_text}'")
    print("-" * 80)
    
    query = MemoryQuery(
        query=query_text,
        top_k=5
    )
    
    results = memory_service.search_memories(query)
    
    print(f"Found {len(results)} results:\n")
    
    for i, result in enumerate(results, 1):
        print(f"{i}. Score: {result.score:.4f}")
        print(f"   Title: {result.item.title}")
        print(f"   Content: {result.item.content[:100]}...")
        print(f"   Date: {result.item.created_at}")
        print()
