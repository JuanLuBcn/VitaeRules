"""
Test intent detection for list management.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from app.crews.capture.planner import plan_from_input


def test_list_intent():
    """Test that list operations are correctly detected."""
    
    test_cases = [
        {
            "input": "Añade mantequilla a la lista de la compra",
            "expected_intent": "list.add",
            "language": "Spanish"
        },
        {
            "input": "por favor, añade mantequilla a la lista de la compra",
            "expected_intent": "list.add",
            "language": "Spanish (polite)"
        },
        {
            "input": "Add milk to the shopping list",
            "expected_intent": "list.add",
            "language": "English"
        },
        {
            "input": "Please add butter to grocery list",
            "expected_intent": "list.add",
            "language": "English (polite)"
        },
        {
            "input": "Add butter to grocery list",
            "expected_intent": "list.add",
            "language": "English"
        },
        {
            "input": "Remember that John likes coffee",
            "expected_intent": "memory.note",
            "language": "English"
        },
        {
            "input": "Remove eggs from the shopping list",
            "expected_intent": "list.remove",
            "language": "English"
        },
        {
            "input": "Remind me to call John tomorrow",
            "expected_intent": "task.create",
            "language": "English"
        },
    ]
    
    print("=" * 80)
    print("INTENT DETECTION TEST - LIST MANAGEMENT")
    print("=" * 80)
    print()
    
    results = []
    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['language']}")
        print(f"Input: \"{test['input']}\"")
        print(f"Expected: {test['expected_intent']}")
        
        try:
            plan = plan_from_input(test['input'], chat_id="test", user_id="test")
            actual = plan.intent
            passed = actual == test['expected_intent']
            
            print(f"Actual: {actual}")
            print(f"Result: {'✅ PASS' if passed else '❌ FAIL'}")
            print(f"Confidence: {plan.confidence:.2f}")
            print(f"Reasoning: {plan.reasoning}")
            
            results.append({
                "test": test['input'],
                "expected": test['expected_intent'],
                "actual": actual,
                "passed": passed
            })
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append({
                "test": test['input'],
                "expected": test['expected_intent'],
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


if __name__ == "__main__":
    test_list_intent()
