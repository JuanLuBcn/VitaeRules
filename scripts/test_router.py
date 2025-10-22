"""
Test the Router (not the Planner) with list management inputs.
This is the FIRST step in the bot flow - before the planner.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from app.llm import get_llm_service
from app.llm.router import ConversationalRouter, ConversationContext

def test_router():
    """Test router with list management inputs."""
    
    test_cases = [
        {
            "input": "Añade mantequilla a la lista de la compra",
            "expected": "list_manage",
            "language": "Spanish"
        },
        {
            "input": "por favor, añade mantequilla a la lista de la compra",
            "expected": "list_manage",
            "language": "Spanish (polite)"
        },
        {
            "input": "Add milk to the shopping list",
            "expected": "list_manage",
            "language": "English"
        },
        {
            "input": "Remind me to call John tomorrow",
            "expected": "task_create",
            "language": "English"
        },
        {
            "input": "Remember that John likes coffee",
            "expected": "note_taking",
            "language": "English"
        },
    ]
    
    print("=" * 80)
    print("ROUTER INTENT DETECTION TEST")
    print("=" * 80)
    print()
    
    llm = get_llm_service()
    router = ConversationalRouter(llm)
    
    results = []
    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['language']}")
        print(f"Input: \"{test['input']}\"")
        print(f"Expected: {test['expected']}")
        
        try:
            context = ConversationContext(
                user_message=test['input'],
                chat_id="test",
                user_id="test",
                conversation_history=[]
            )
            
            decision = router.route(context)
            actual = decision.intent.value
            passed = actual == test['expected']
            
            print(f"Actual: {actual}")
            print(f"Result: {'✅ PASS' if passed else '❌ FAIL'}")
            print(f"Confidence: {decision.confidence:.2%}")
            print(f"Response: {decision.conversational_response}")
            print(f"Reasoning: {decision.reasoning}")
            
            results.append({
                "test": test['input'],
                "expected": test['expected'],
                "actual": actual,
                "passed": passed
            })
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "test": test['input'],
                "expected": test['expected'],
                "actual": "ERROR",
                "passed": False
            })
        
        print()
        print("-" * 80)
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    passed = sum(1 for r in results if r['passed'])
    total = len(results)
    print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    print()
    
    for r in results:
        status = "✅" if r['passed'] else "❌"
        print(f"{status} {r['test'][:50]}")
        if not r['passed']:
            print(f"   Expected: {r['expected']}, Got: {r['actual']}")
    
    print()
    
    if passed < total:
        print("⚠️  ROUTER needs to be fixed - this runs BEFORE the planner!")
        print("   The router is the FIRST step that detects intent in the bot.")
    else:
        print("✅ Router is working correctly!")


if __name__ == "__main__":
    test_router()
