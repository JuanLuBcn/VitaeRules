import sys
sys.path.insert(0, 'src')

import asyncio
from app.tools.task_tool import TaskTool
from app.tools.list_tool import ListTool

async def check_data():
    print("\n" + "=" * 80)
    print("DATABASE STATUS CHECK")
    print("=" * 80)
    
    # Check tasks
    print("\n📋 TASKS:")
    try:
        task_tool = TaskTool()
        result = await task_tool.execute({
            "operation": "list_tasks",
            "user_id": "default",
            "chat_id": "default"
        })
        task_count = len(result.get('tasks', []))
        if task_count == 0:
            print("   ❌ NO TASKS IN DATABASE")
        else:
            print(f"   ✓ Found {task_count} tasks")
            for task in result['tasks'][:3]:
                print(f"     - {task.get('description', 'No description')[:60]}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Check lists
    print("\n📝 LISTS:")
    try:
        list_tool = ListTool()
        result = await list_tool.execute({
            "operation": "get_lists",
            "user_id": "default",
            "chat_id": "default"
        })
        list_count = len(result.get('lists', []))
        if list_count == 0:
            print("   ❌ NO LISTS IN DATABASE")
        else:
            print(f"   ✓ Found {list_count} lists")
            for lst in result['lists'][:3]:
                print(f"     - {lst.get('name', 'Unnamed')}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Check memories (simplified)
    print("\n💭 MEMORIES:")
    import chromadb
    try:
        client = chromadb.PersistentClient(path="data/chroma")
        collections = client.list_collections()
        if not collections:
            print("   ❌ NO MEMORY COLLECTIONS IN CHROMA")
        else:
            print(f"   Found {len(collections)} collection(s)")
            for coll in collections:
                count = coll.count()
                print(f"     - {coll.name}: {count} memories")
                if count == 0:
                    print("       ❌ This collection is EMPTY")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 80)
    print("CONCLUSION:")
    print("=" * 80)
    print("The bot CANNOT find information because there's NOTHING STORED YET!")
    print("You need to add memories, tasks, or lists first before searching.")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    asyncio.run(check_data())
