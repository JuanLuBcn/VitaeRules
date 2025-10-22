"""
Test the item parsing logic for list management.
"""

import re

def parse_list_items(text: str) -> list[str]:
    """Parse comma-separated or conjunction-separated items."""
    # Split by comma, "y", "and"
    items = re.split(r'[,;]|\s+y\s+|\s+and\s+', text)
    items = [item.strip() for item in items if item.strip()]
    return items


test_cases = [
    ("Berenjenas, tomates y aguacates", ["Berenjenas", "tomates", "aguacates"]),
    ("milk, eggs and bread", ["milk", "eggs", "bread"]),
    ("mantequilla", ["mantequilla"]),
    ("apples, oranges, bananas", ["apples", "oranges", "bananas"]),
    ("pan y leche", ["pan", "leche"]),
]

print("=" * 80)
print("ITEM PARSING TEST")
print("=" * 80)
print()

for text, expected in test_cases:
    result = parse_list_items(text)
    passed = result == expected
    
    print(f"Input: '{text}'")
    print(f"Expected: {expected}")
    print(f"Got: {result}")
    print(f"Result: {'✅ PASS' if passed else '❌ FAIL'}")
    print()

print("=" * 80)
