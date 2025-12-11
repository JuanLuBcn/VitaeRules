import sys
sys.path.insert(0, 'src')

from app.tools.memory_search_tool import MemorySearchTool
from app.memory.api import MemoryService

print("\n" + "=" * 80)
print("TESTING MEMORY SEARCH TOOL")
print("=" * 80)

# Initialize tool
memory_service = MemoryService()
tool = MemorySearchTool(memory_service=memory_service)

# Test search
print("\n🔍 Searching for: 'David piso 180000 euros'")
result = tool._run(query="David piso 180000 euros", limit=3)

print("\n📋 RESULTS:")
print(result)

print("\n" + "=" * 80)
