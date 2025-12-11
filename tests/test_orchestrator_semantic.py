"""
Quick test to verify orchestrator uses semantic-only analysis (no examples).

This tests that the orchestrator prompt:
1. Doesn't rely on examples
2. Uses semantic understanding
3. Makes correct tool decisions
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.llm import LLMService
from app.memory import MemoryService
from app.agents.orchestrator import ConversationalOrchestrator


async def test_semantic_analysis():
    """Test semantic-only message analysis."""
    
    print("\n" + "="*70)
    print("ORCHESTRATOR SEMANTIC ANALYSIS TEST")
    print("="*70)
    
    # Initialize services
    llm = LLMService()
    memory = MemoryService()
    orchestrator = ConversationalOrchestrator(llm, memory)
    
    test_cases = [
        {
            "message": "María me dijo que se muda a Barcelona",
            "expected_tool": "save_note",
            "description": "Affirmation - should store"
        },
        {
            "message": "¿Qué me dijo María sobre Barcelona?",
            "expected_tool": "search_memory",
            "description": "Query about past conversation - should search"
        },
        {
            "message": "¿Qué opinas de Barcelona?",
            "expected_tool": None,
            "description": "General chat - NO tool, just conversation"
        },
        {
            "message": "Recuérdame llamar a Juan",
            "expected_tool": None,  # Will ask "¿Cuándo?"
            "description": "Task - needs more info (when?)"
        },
        {
            "message": "Leche",
            "expected_tool": None,  # Will ask "¿A qué lista?"
            "description": "List item - needs more info (which list?)"
        },
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'─'*70}")
        print(f"TEST {i}: {test['description']}")
        print(f"{'─'*70}")
        print(f"📝 Message: \"{test['message']}\"")
        print(f"🎯 Expected tool: {test['expected_tool'] or 'None (conversation)'}")
        
        try:
            # Call the internal _analyze_message method directly
            analysis = await orchestrator._analyze_message(test['message'], None)
            
            reply = analysis.get("reply", "")
            tool_call = analysis.get("tool_call")
            tool_name = tool_call.get("name") if tool_call else None
            
            print(f"\n🤖 LLM Response:")
            print(f"   Reply: {reply}")
            print(f"   Tool: {tool_name or 'None'}")
            
            if tool_call:
                print(f"   Args: {tool_call.get('args', {})}")
            
            # Check if tool matches expectation
            if tool_name == test['expected_tool']:
                print(f"\n✅ CORRECT - Tool matches expectation")
            elif test['expected_tool'] is None and tool_name is None:
                print(f"\n✅ CORRECT - No tool (conversational as expected)")
            else:
                print(f"\n❌ MISMATCH - Expected {test['expected_tool']}, got {tool_name}")
        
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("TEST COMPLETED")
    print("="*70)
    print("\n✅ The orchestrator should now use semantic understanding")
    print("   (no hardcoded examples, pure meaning analysis)")
    print("\n")


if __name__ == "__main__":
    asyncio.run(test_semantic_analysis())
