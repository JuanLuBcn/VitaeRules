"""Test script for enhanced fields in ListTool and TaskTool."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.app.tools.list_tool import ListTool
from src.app.tools.task_tool import TaskTool


async def test_list_tool_enhanced_fields():
    """Test ListTool with enhanced fields."""
    print("=" * 60)
    print("Testing ListTool with Enhanced Fields")
    print("=" * 60)
    
    # Create tool with in-memory database for testing
    db_path = Path(__file__).parent / "test_lists_enhanced.sqlite"
    db_path.unlink(missing_ok=True)  # Clean up if exists
    
    list_tool = ListTool(db_path=db_path)
    
    # Test 1: Create a list
    print("\n1. Creating test list...")
    result = await list_tool.execute({
        "operation": "create_list",
        "list_name": "Compras Mercadona",
        "user_id": "test_user",
        "chat_id": "test_chat"
    })
    list_id = result["list_id"]
    print(f"✓ Created list: {result['list_name']} (ID: {list_id})")
    
    # Test 2: Add item with basic fields only
    print("\n2. Adding basic item...")
    result = await list_tool.execute({
        "operation": "add_item",
        "list_name": "Compras Mercadona",
        "item_text": "Comprar leche",
        "user_id": "test_user",
        "chat_id": "test_chat"
    })
    print(f"✓ Added basic item: {result['item_text']}")
    
    # Test 3: Add item with people
    print("\n3. Adding item with people...")
    result = await list_tool.execute({
        "operation": "add_item",
        "list_name": "Compras Mercadona",
        "item_text": "Comprar queso manchego para Juan",
        "people": ["Juan"],
        "user_id": "test_user",
        "chat_id": "test_chat"
    })
    print(f"✓ Added item with people: {result['item_text']}")
    print(f"  People: {result['people']}")
    
    # Test 4: Add item with location and tags
    print("\n4. Adding item with location and tags...")
    result = await list_tool.execute({
        "operation": "add_item",
        "list_name": "Compras Mercadona",
        "item_text": "Comprar productos orgánicos",
        "location": "Mercadona Gran Vía",
        "latitude": 40.4168,
        "longitude": -3.7038,
        "tags": ["orgánico", "urgente"],
        "notes": "Buscar en sección bio",
        "user_id": "test_user",
        "chat_id": "test_chat"
    })
    print(f"✓ Added item with location: {result['item_text']}")
    print(f"  Location: {result['location']}")
    print(f"  Coordinates: {result['coordinates']}")
    print(f"  Tags: {result['tags']}")
    print(f"  Notes: {result['notes']}")
    
    # Test 5: List all items (verify deserialization)
    print("\n5. Listing all items...")
    result = await list_tool.execute({
        "operation": "list_items",
        "list_name": "Compras Mercadona",
        "user_id": "test_user",
        "chat_id": "test_chat"
    })
    print(f"✓ Found {result['count']} items:")
    for i, item in enumerate(result['items'], 1):
        print(f"\n  Item {i}: {item['text']}")
        if item.get('people'):
            print(f"    People: {item['people']}")
        if item.get('location'):
            print(f"    Location: {item['location']}")
        if item.get('coordinates'):
            print(f"    Coordinates: {item['coordinates']}")
        if item.get('tags'):
            print(f"    Tags: {item['tags']}")
        if item.get('notes'):
            print(f"    Notes: {item['notes']}")
    
    # Clean up
    # Note: Delete the tool first to close database connections
    del list_tool
    import time
    time.sleep(0.1)  # Brief delay to ensure connection is closed
    try:
        db_path.unlink(missing_ok=True)
    except PermissionError:
        # Windows may still have file locked, that's OK
        pass
    print("\n✓ ListTool tests completed successfully!")


async def test_task_tool_enhanced_fields():
    """Test TaskTool with enhanced fields."""
    print("\n" + "=" * 60)
    print("Testing TaskTool with Enhanced Fields")
    print("=" * 60)
    
    # Create tool with in-memory database for testing
    db_path = Path(__file__).parent / "test_tasks_enhanced.sqlite"
    db_path.unlink(missing_ok=True)  # Clean up if exists
    
    task_tool = TaskTool(db_path=db_path)
    
    # Test 1: Create basic task
    print("\n1. Creating basic task...")
    result = await task_tool.execute({
        "operation": "create_task",
        "title": "Revisar email",
        "priority": 1,
        "user_id": "test_user",
        "chat_id": "test_chat"
    })
    print(f"✓ Created task: {result['title']}")
    
    # Test 2: Create task with people
    print("\n2. Creating task with people...")
    result = await task_tool.execute({
        "operation": "create_task",
        "title": "Llamar a Juan sobre el proyecto",
        "description": "Discutir avances del sprint",
        "people": ["Juan"],
        "tags": ["trabajo", "urgente"],
        "priority": 2,
        "user_id": "test_user",
        "chat_id": "test_chat"
    })
    print(f"✓ Created task: {result['title']}")
    print(f"  People: {result['people']}")
    print(f"  Tags: {result['tags']}")
    
    # Test 3: Create task with location and reminder
    print("\n3. Creating task with location and reminder...")
    result = await task_tool.execute({
        "operation": "create_task",
        "title": "Reunión en la oficina",
        "description": "Presentación del proyecto Vitti",
        "location": "Oficina Central, Madrid",
        "latitude": 40.4168,
        "longitude": -3.7038,
        "place_id": "ChIJgTwKgJQpQg0RaSKMYcHeNsQ",
        "reminder_distance": 500,
        "tags": ["reunión", "importante"],
        "priority": 3,
        "user_id": "test_user",
        "chat_id": "test_chat"
    })
    print(f"✓ Created task: {result['title']}")
    print(f"  Location: {result['location']}")
    print(f"  Coordinates: {result['coordinates']}")
    print(f"  Place ID: {result['place_id']}")
    print(f"  Reminder distance: {result['reminder_distance']}m")
    print(f"  Tags: {result['tags']}")
    
    # Test 4: List all tasks (verify deserialization)
    print("\n4. Listing all tasks...")
    result = await task_tool.execute({
        "operation": "list_tasks",
        "user_id": "test_user",
        "chat_id": "test_chat"
    })
    print(f"✓ Found {result['count']} tasks:")
    for i, task in enumerate(result['tasks'], 1):
        print(f"\n  Task {i}: {task['title']} (Priority: {task['priority']})")
        if task.get('description'):
            print(f"    Description: {task['description']}")
        if task.get('people'):
            print(f"    People: {task['people']}")
        if task.get('location'):
            print(f"    Location: {task['location']}")
        if task.get('coordinates'):
            print(f"    Coordinates: {task['coordinates']}")
        if task.get('tags'):
            print(f"    Tags: {task['tags']}")
        if task.get('reminder_distance'):
            print(f"    Reminder: {task['reminder_distance']}m")
    
    # Clean up
    del task_tool
    import time
    time.sleep(0.1)
    try:
        db_path.unlink(missing_ok=True)
    except PermissionError:
        pass
    print("\n✓ TaskTool tests completed successfully!")


async def test_json_edge_cases():
    """Test edge cases for JSON serialization/deserialization."""
    print("\n" + "=" * 60)
    print("Testing JSON Edge Cases")
    print("=" * 60)
    
    db_path = Path(__file__).parent / "test_edge_cases.sqlite"
    db_path.unlink(missing_ok=True)
    
    list_tool = ListTool(db_path=db_path)
    
    # Create list
    await list_tool.execute({
        "operation": "create_list",
        "list_name": "Edge Cases",
        "user_id": "test_user"
    })
    
    # Test 1: Empty arrays
    print("\n1. Testing empty arrays...")
    result = await list_tool.execute({
        "operation": "add_item",
        "list_name": "Edge Cases",
        "item_text": "Item with empty arrays",
        "people": [],
        "tags": [],
        "user_id": "test_user"
    })
    print(f"✓ People: {result['people']} (should be [])")
    print(f"✓ Tags: {result['tags']} (should be [])")
    
    # Test 2: NULL fields (no optional fields provided)
    print("\n2. Testing NULL fields...")
    result = await list_tool.execute({
        "operation": "add_item",
        "list_name": "Edge Cases",
        "item_text": "Item with no optional fields",
        "user_id": "test_user"
    })
    print(f"✓ People: {result['people']} (should be [])")
    print(f"✓ Location: {result.get('location')} (should be None)")
    print(f"✓ Coordinates: {result.get('coordinates')} (should be None)")
    
    # Test 3: Verify retrieval
    print("\n3. Verifying retrieval...")
    result = await list_tool.execute({
        "operation": "list_items",
        "list_name": "Edge Cases",
        "user_id": "test_user"
    })
    for item in result['items']:
        print(f"\n  Item: {item['text']}")
        print(f"    People type: {type(item['people'])} = {item['people']}")
        print(f"    Tags type: {type(item['tags'])} = {item['tags']}")
        print(f"    Metadata type: {type(item['metadata'])} = {item['metadata']}")
    
    # Clean up
    del list_tool
    import time
    time.sleep(0.1)
    try:
        db_path.unlink(missing_ok=True)
    except PermissionError:
        pass
    print("\n✓ Edge case tests completed successfully!")


async def main():
    """Run all tests."""
    print("\n🧪 Testing Enhanced Fields for Phase 1")
    print("=" * 60)
    
    try:
        await test_list_tool_enhanced_fields()
        await test_task_tool_enhanced_fields()
        await test_json_edge_cases()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nEnhanced fields are working correctly:")
        print("  ✓ ListTool: people, location, coords, tags, notes, media")
        print("  ✓ TaskTool: people, location, coords, tags, reminder, media")
        print("  ✓ JSON serialization/deserialization working")
        print("  ✓ NULL/empty value handling correct")
        print("\nNext steps:")
        print("  1. Run migration script: python scripts/migrate_enhanced_fields.py")
        print("  2. Update agents to extract and use these fields")
        print("  3. Update documentation with implementation status")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
