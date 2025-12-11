import sys
sys.path.insert(0, 'src')

import asyncio
from app.memory.api import MemoryService
from app.memory.schemas import MemoryQuery

async def test_search():
    print("\n" + "=" * 80)
    print("TESTING MEMORY SEARCH FOR DAVID'S APARTMENT")
    print("=" * 80 + "\n")
    
    memory_service = MemoryService()
    
    # Test the exact query
    query = MemoryQuery(
        query="David piso apartamento compra precio",
        user_id="8210122217",  # Using the actual user_id from memories
        chat_id="8210122217",
        limit=10
    )
    
    print(f"Query: {query.query}")
    print(f"User ID: {query.user_id}")
    print(f"Chat ID: {query.chat_id}\n")
    
    results = await memory_service.search(query)
    
    print(f"Total results found: {len(results.results)}\n")
    
    if results.results:
        print("RESULTS:")
        for i, mem in enumerate(results.results):
            print(f"\n{i+1}. Score: {mem.score:.4f}")
            print(f"   Content: {mem.content[:200]}...")
            print(f"   Created: {mem.created_at}")
    else:
        print("❌ NO RESULTS FOUND")
        print("\nThis means the search correctly found nothing.")
        print("The bot's answer of '180,000 euros' was HALLUCINATED!")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test_search())
