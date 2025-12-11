import sys
sys.path.insert(0, 'src')

from app.memory.api import MemoryService
from app.memory.schemas import MemoryItem, MemorySource, MemoryQuery

def test_store_and_retrieve():
    print("\n" + "=" * 80)
    print("TESTING MEMORY STORAGE AND RETRIEVAL")
    print("=" * 80)
    
    memory_service = MemoryService()
    
    # Test 1: Store a new memory
    print("\n1. STORING NEW MEMORY:")
    test_memory = MemoryItem(
        content="David compró su piso por 180,000 euros en enero de 2023",
        title="Compra de piso de David",
        user_id="8210122217",
        chat_id="8210122217",
        source=MemorySource.CAPTURE,
        tags=["David", "piso", "compra", "180000"],
        people=["David"]
    )
    
    try:
        result = memory_service.save_memory(test_memory)
        print(f"   ✓ Memory stored successfully!")
        print(f"   Memory ID: {result.id}")
        print(f"   Content: {result.content}")
    except Exception as e:
        print(f"   ❌ ERROR storing memory: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 2: Retrieve the memory we just stored
    print("\n2. RETRIEVING MEMORY (specific search):")
    try:
        query = MemoryQuery(
            query="David piso 180000 euros",
            top_k=5
        )
        search_results = memory_service.search_memories(query)
        print(f"   Found {len(search_results)} results")
        
        if search_results:
            for i, result in enumerate(search_results):
                print(f"\n   Result {i+1}:")
                print(f"   - Content: {result.item.content[:100]}...")
                print(f"   - Score: {result.score}")
                print(f"   - Created: {result.item.created_at}")
        else:
            print("   ❌ NO RESULTS - Memory was stored but not retrieved!")
    except Exception as e:
        print(f"   ❌ ERROR retrieving memory: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: Count total memories
    print("\n3. CHECKING TOTAL MEMORIES:")
    try:
        import chromadb
        client = chromadb.PersistentClient(path="data/chroma")
        collection = client.get_collection("memories")
        total = collection.count()
        print(f"   Total memories in Chroma: {total}")
        
        # Get last 3 memories
        results = collection.get(
            limit=3,
            include=['documents', 'metadatas']
        )
        print(f"\n   Last 3 memories:")
        for i, (doc, meta) in enumerate(zip(results['documents'], results['metadatas'])):
            print(f"   {i+1}. {doc[:80]}...")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    test_store_and_retrieve()
