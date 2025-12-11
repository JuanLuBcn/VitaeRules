
import os
import sys
from app.memory.api import MemoryService
from app.tools.memory_search_tool import MemorySearchTool

# Mock settings
os.environ["APP_ENV"] = "dev"

def test_memory_search():
    print("Initializing MemoryService...")
    memory_service = MemoryService()
    
    print("Initializing MemorySearchTool...")
    tool = MemorySearchTool(memory_service=memory_service)
    
    print("Running search...")
    try:
        result = tool._run(query="Cuanto costó el piso de david?")
        print(f"Result: {result}")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_memory_search()
