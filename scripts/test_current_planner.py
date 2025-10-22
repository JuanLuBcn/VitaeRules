"""
Quick test of CURRENT planner code with the exact input from the bot.
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from app.crews.capture.planner import plan_from_input

# Exact input from the bot
user_input = "Añade mantequilla a la lista de la compra"

print("=" * 80)
print("TESTING CURRENT PLANNER CODE")
print("=" * 80)
print(f"Input: {user_input}")
print()

plan = plan_from_input(user_input, chat_id="test", user_id="test")

print(f"Intent: {plan.intent}")
print(f"Intent value: {plan.intent.value if hasattr(plan.intent, 'value') else plan.intent}")
print(f"Confidence: {plan.confidence:.2%}")
print(f"Reasoning: {plan.reasoning}")
print()

if plan.intent == "list.add" or (hasattr(plan.intent, 'value') and plan.intent.value == "list.add"):
    print("✅ CORRECT: Detected as list.add")
else:
    print(f"❌ WRONG: Detected as {plan.intent}")
    print()
    print("This means the BOT NEEDS TO BE RESTARTED to pick up the new planner code!")
