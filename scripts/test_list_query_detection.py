"""
Test list query detection.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from app.adapters.question_detection import is_list_query, extract_list_name


def test_list_query_detection():
    """Test that list queries are detected correctly."""
    
    test_cases = [
        {
            "input": "Qué hay en la lista de la compra?",
            "expected_query": True,
            "expected_name": "lista de la compra",
            "language": "Spanish"
        },
        {
            "input": "What's on my shopping list?",
            "expected_query": True,
            "expected_name": "lista de la compra",
            "language": "English"
        },
        {
            "input": "Muestra la lista de la compra",
            "expected_query": True,
            "expected_name": "lista de la compra",
            "language": "Spanish"
        },
        {
            "input": "Añade mantequilla a la lista",
            "expected_query": False,
            "expected_name": None,
            "language": "Spanish (not a query)"
        },
        {
            "input": "What did I do yesterday?",
            "expected_query": False,
            "expected_name": None,
            "language": "English (not a list query)"
        },
    ]
    
    print("=" * 80)
    print("LIST QUERY DETECTION TEST")
    print("=" * 80)
    print()
    
    results = []
    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['language']}")
        print(f"Input: \"{test['input']}\"")
        
        is_query = is_list_query(test['input'])
        list_name = extract_list_name(test['input']) if is_query else None
        
        query_pass = is_query == test['expected_query']
        
        print(f"Is list query: {is_query} (expected: {test['expected_query']}) {'✅' if query_pass else '❌'}")
        
        if is_query:
            print(f"Extracted list name: {list_name}")
        
        results.append(query_pass)
        print()
        print("-" * 80)
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    print()
    
    if passed == total:
        print("✅ All tests passed! List query detection is working.")
    else:
        print("⚠️ Some tests failed.")


if __name__ == "__main__":
    test_list_query_detection()
