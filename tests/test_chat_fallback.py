"""
Test Chat Fallback when Memory Search Returns Empty

This tests the transparent fallback from MEMORY_QUERY to CHAT
when no memories are found.

Expected behavior:
1. User asks about something not in memory
2. System searches memory → empty
3. System transparently falls back to chat
4. Offers to store information or provides helpful response
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app.llm import LLMService
from app.memory import MemoryService
from app.agents.orchestrator import ConversationalOrchestrator


async def test_chat_fallback():
    """Test memory query fallback to chat."""
    
    print("\n" + "="*60)
    print("CHAT FALLBACK TEST")
    print("="*60)
    
    # Initialize services
    llm = LLMService()
    memory = MemoryService()
    orchestrator = ConversationalOrchestrator(llm, memory)
    
    # Test cases that should trigger search → empty → chat fallback
    test_cases = [
        {
            "message": "¿Qué me dijo María sobre Barcelona?",
            "description": "Personal query (should offer to store)",
            "expected_behavior": "Offer to store information"
        },
        {
            "message": "¿Cuándo es el cumpleaños de Juan?",
            "description": "Personal date query",
            "expected_behavior": "Ask when it is and offer to save"
        },
        {
            "message": "¿Qué sabes de Python?",
            "description": "General knowledge (ambiguous)",
            "expected_behavior": "Provide general answer or ask to store specific info"
        },
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'─'*60}")
        print(f"TEST {i}: {test['description']}")
        print(f"{'─'*60}")
        print(f"📝 User: {test['message']}")
        print(f"🎯 Expected: {test['expected_behavior']}")
        
        try:
            result = await orchestrator.handle_message(
                message=test['message'],
                chat_id=f"test_{i}",
                user_id="test_user"
            )
            
            print(f"\n🤖 Bot Response:")
            print(f"   {result['message']}")
            print(f"\n⏸️  Waiting for input: {result.get('waiting_for_input', False)}")
            
            # Check if response indicates fallback happened
            response_lower = result['message'].lower()
            
            is_fallback = any([
                "no encontré" in response_lower,
                "no tengo" in response_lower,
                "quieres que guarde" in response_lower,
                "te lo guardo" in response_lower,
                "te lo anoto" in response_lower,
            ])
            
            if is_fallback:
                print("✅ FALLBACK DETECTED - Bot offered to store or said 'not found'")
            else:
                print("⚠️  UNKNOWN RESPONSE - Check if it's appropriate")
        
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("TEST COMPLETED")
    print("="*60)
    print("\n✅ Expected behavior:")
    print("   1. Bot searches memory (finds nothing)")
    print("   2. Bot transparently falls back to chat")
    print("   3. Bot either:")
    print("      - Offers to store the information")
    print("      - Provides helpful general response")
    print("   4. User doesn't see 'error' - seamless experience")
    print("\n")


if __name__ == "__main__":
    asyncio.run(test_chat_fallback())
