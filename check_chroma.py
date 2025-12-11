import sys
sys.path.insert(0, 'src')

import asyncio
from app.memory.api import MemoryService
from app.tools.task_tool import TaskTool
from app.tools.list_tool import ListTool

async def check_data():
    print("=" * 80)
    print("CHECKING STORED DATA")
    print("=" * 80)
    
    # Check memories
    print("\n1. CHECKING MEMORIES (Chroma):")
    try:
        memory_service = MemoryService()
        # Try to get all memories
        from app.models.memory import MemoryQuery
        query = MemoryQuery(
            query="David piso apartamento compra",
            user_id="default",
            chat_id="default",
            limit=10
        )
        results = await memory_service.search(query)
        print(f"   Found {len(results.results)} memories")
        if results.results:
            print("\n   Sample memories:")
            for i, mem in enumerate(results.results[:5]):
                print(f"   {i+1}. {mem.content[:200]}...")
                print(f"      Score: {mem.score}, Created: {mem.created_at}")
        else:
            print("   ❌ NO MEMORIES FOUND IN DATABASE")
    except Exception as e:
        print(f"   Error checking memories: {e}")
    
    # Check tasks
    print("\n2. CHECKING TASKS:")
    try:
        task_tool = TaskTool()
        result = await task_tool.execute({
            "operation": "list_tasks",
            "user_id": "default",
            "chat_id": "default"
        })
        print(f"   {result.get('message', 'No message')}")
        if 'tasks' in result:
            print(f"   Found {len(result['tasks'])} tasks")
            for task in result['tasks'][:5]:
                status = "✓" if task.get('completed') else "○"
                print(f"   {status} {task.get('description', 'No description')[:80]}")
        else:
            print("   ❌ NO TASKS FOUND IN DATABASE")
    except Exception as e:
        print(f"   Error checking tasks: {e}")
    
    # Check lists
    print("\n3. CHECKING LISTS:")
    try:
        list_tool = ListTool()
        result = await list_tool.execute({
            "operation": "get_lists",
            "user_id": "default",
            "chat_id": "default"
        })
        print(f"   {result.get('message', 'No message')}")
        if 'lists' in result:
            print(f"   Found {len(result['lists'])} lists")
            for lst in result['lists'][:5]:
                item_count = len(lst.get('items', []))
                print(f"   - {lst.get('name', 'Unnamed')} ({item_count} items)")
        else:
            print("   ❌ NO LISTS FOUND IN DATABASE")
    except Exception as e:
        print(f"   Error checking lists: {e}")
    
    print("\n" + "=" * 80)
    print("CONCLUSION:")
    print("=" * 80)
    print("If all checks show ❌ NO DATA, then the database is empty.")
    print("The bot cannot find information because there's nothing stored yet!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(check_data())
