"""Test NoteAgent save_memory fix."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from app.agents import NoteAgent
from app.llm import LLMService
from app.memory import MemoryService


async def test_note_save():
    """Test saving a note."""
    print("Testing NoteAgent.execute_confirmed()...")
    
    llm = LLMService()
    memory = MemoryService()
    agent = NoteAgent(llm, memory)
    
    # Simulate confirmed note data
    data = {
        "note_data": {
            "content": "Test note content",
            "title": "Test Note",
            "people": ["John"],
            "places": [],
            "tags": ["test"],
        },
        "chat_id": "test_chat",
        "user_id": "test_user",
    }
    
    try:
        result = await agent.execute_confirmed(data)
        
        if result.success:
            print("✅ SUCCESS: Note saved!")
            print(f"   Message: {result.message}")
        else:
            print(f"❌ FAILED: {result.error}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_note_save())
