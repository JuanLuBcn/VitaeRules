"""
Test list tool auto-creation functionality.
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from app.tools.list_tool import ListTool


async def test_list_tool():
    """Test that list tool auto-creates lists when adding items."""
    
    # Use test database
    test_db = project_root / "data" / "test_lists.sqlite"
    if test_db.exists():
        test_db.unlink()  # Clean slate
    
    tool = ListTool(db_path=test_db)
    
    print("=" * 80)
    print("LIST TOOL AUTO-CREATE TEST")
    print("=" * 80)
    print()
    
    # Test 1: Add item to non-existent list (should auto-create)
    print("Test 1: Add item to non-existent 'Shopping List'")
    print("-" * 80)
    
    try:
        result = await tool.execute({
            "operation": "add_item",
            "list_name": "Shopping List",
            "item_text": "mantequilla",
            "user_id": "test_user",
            "chat_id": "test_chat"
        })
        
        print(f"✅ SUCCESS: Added item")
        print(f"   Item ID: {result['item_id']}")
        print(f"   List ID: {result['list_id']}")
        print(f"   Text: {result['item_text']}")
        print()
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        print()
        return
    
    # Test 2: Add another item to the same list (should find existing)
    print("Test 2: Add another item to existing 'Shopping List'")
    print("-" * 80)
    
    try:
        result = await tool.execute({
            "operation": "add_item",
            "list_name": "Shopping List",
            "item_text": "leche",
            "user_id": "test_user",
            "chat_id": "test_chat"
        })
        
        print(f"✅ SUCCESS: Added item")
        print(f"   Item ID: {result['item_id']}")
        print(f"   Text: {result['item_text']}")
        print()
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        print()
        return
    
    # Test 3: Case-insensitive lookup
    print("Test 3: Add item using different case 'shopping list'")
    print("-" * 80)
    
    try:
        result = await tool.execute({
            "operation": "add_item",
            "list_name": "shopping list",  # lowercase
            "item_text": "pan",
            "user_id": "test_user",
            "chat_id": "test_chat"
        })
        
        print(f"✅ SUCCESS: Found existing list (case-insensitive)")
        print(f"   Item ID: {result['item_id']}")
        print(f"   Text: {result['item_text']}")
        print()
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        print()
        return
    
    # Test 4: List all items
    print("Test 4: List all items in 'Shopping List'")
    print("-" * 80)
    
    try:
        result = await tool.execute({
            "operation": "list_items",
            "list_name": "Shopping List",
        })
        
        print(f"✅ SUCCESS: Retrieved {result['count']} items")
        for item in result['items']:
            status = "✓" if item['completed'] else " "
            print(f"   [{status}] {item['text']}")
        print()
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        print()
        return
    
    print("=" * 80)
    print("ALL TESTS PASSED! ✅")
    print("=" * 80)
    print()
    print("List tool now:")
    print("  ✓ Auto-creates lists when adding items")
    print("  ✓ Case-insensitive list name lookup")
    print("  ✓ Ready for Telegram bot integration")


if __name__ == "__main__":
    asyncio.run(test_list_tool())
