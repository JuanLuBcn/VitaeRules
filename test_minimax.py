"""
Quick test for minimax-m2:cloud model
"""

import asyncio
import time
from crewai import Agent, Task, Crew, LLM


# Test cases with expected intent
TEST_CASES = [
    # SEARCH intent (questions)
    ("What is in my shopping list?", "SEARCH"),
    ("What did I do last Tuesday?", "SEARCH"),
    ("What is my cat's name?", "SEARCH"),
    ("When is my doctor appointment?", "SEARCH"),
    ("Do I have any tasks for today?", "SEARCH"),
    ("Who built the Sagrada Familia?", "SEARCH"),
    ("Dónde dejé las llaves?", "SEARCH"),
    ("Qué tengo que hacer mañana?", "SEARCH"),
    
    # ACTION intent (statements, commands, greetings)
    ("Add tomatoes to shopping list", "ACTION"),
    ("Hoy fuimos a la oficina con Biel", "ACTION"),
    ("Her name is Luna, she's 3 years old", "ACTION"),
    ("Hello", "ACTION"),
    ("Thanks!", "ACTION"),
    ("Create a task to call the doctor", "ACTION"),
    ("I'm feeling tired today", "ACTION"),
    ("Añade leche a la lista de la compra", "ACTION"),
    ("Recuérdame que mañana tengo dentista", "ACTION"),
    ("Hoy he visto a María en el parque", "ACTION"),
]


def create_intent_agent(llm) -> Agent:
    """Create intent analyzer agent."""
    return Agent(
        role="Intent Analyzer",
        goal="Classify user messages as SEARCH or ACTION based on semantic meaning",
        backstory="""You are an expert at understanding user intent from natural language.
        You classify messages into two categories:
        - SEARCH: Questions about information (stored or general knowledge)
        - ACTION: Statements, commands, or information to store (default)
        You focus on semantic meaning, not keywords.""",
        verbose=False,
        allow_delegation=False,
        llm=llm
    )


def create_intent_task(agent: Agent, message: str) -> Task:
    """Create intent classification task."""
    return Task(
        description=f"""Analyze this user message and determine the primary intent:

User message: "{message}"

Classify as ONE of these TWO categories:

**SEARCH**: The user wants to retrieve or query information
- Questions about stored data or general knowledge
- Uses question words: What, When, Where, Who, How, Why, Do, Is, Are

**ACTION**: The user wants to store, create, modify, or communicate (DEFAULT)
- Statements with new information
- Commands to store/modify data
- Social interactions
- When in doubt, choose ACTION

Think about what the user wants to accomplish:
- ASKING for information → SEARCH
- TELLING you something → ACTION

Output format:
Primary Intent: [SEARCH/ACTION]
Reasoning: [Brief explanation]""",
        agent=agent,
        expected_output="Intent classification (SEARCH or ACTION) with reasoning"
    )


async def test_minimax():
    """Test minimax-m2:cloud model."""
    print("="*80)
    print("Testing minimax-m2:cloud")
    print("="*80)
    
    # Create LLM
    print("\n[1] Creating LLM instance...")
    init_start = time.time()
    llm = LLM(
        model="ollama/minimax-m2:cloud",
        base_url="http://localhost:11434",
        temperature=0.7
    )
    init_time = time.time() - init_start
    print(f"✓ LLM initialized in {init_time:.2f}s")
    
    # Create agent (reuse for all tests)
    print("\n[2] Creating agent...")
    agent_start = time.time()
    agent = create_intent_agent(llm)
    agent_time = time.time() - agent_start
    print(f"✓ Agent created in {agent_time:.2f}s")
    
    # Test cases
    print(f"\n[3] Running {len(TEST_CASES)} test cases...")
    print("="*80)
    
    results = {
        "correct": 0,
        "total": len(TEST_CASES),
        "times": [],
        "predictions": []
    }
    
    for i, (message, expected_intent) in enumerate(TEST_CASES, 1):
        try:
            print(f"\n[{i}/{len(TEST_CASES)}] Testing: '{message[:60]}...'")
            
            # Create task
            task = create_intent_task(agent, message)
            
            # Create crew
            crew = Crew(
                agents=[agent],
                tasks=[task],
                verbose=False
            )
            
            # Measure ONLY inference time
            start_time = time.time()
            result = crew.kickoff()
            elapsed_time = time.time() - start_time
            
            # Parse result
            output = result.raw if hasattr(result, 'raw') else str(result)
            output_upper = output.upper()
            
            # Determine predicted intent
            if "PRIMARY INTENT: SEARCH" in output_upper or "INTENT: SEARCH" in output_upper:
                predicted_intent = "SEARCH"
            elif "PRIMARY INTENT: ACTION" in output_upper or "INTENT: ACTION" in output_upper:
                predicted_intent = "ACTION"
            else:
                if "SEARCH" in output_upper and "ACTION" not in output_upper:
                    predicted_intent = "SEARCH"
                else:
                    predicted_intent = "ACTION"
            
            # Check if correct
            is_correct = predicted_intent == expected_intent
            if is_correct:
                results["correct"] += 1
                status = "✓ CORRECT"
            else:
                status = "✗ WRONG"
            
            results["times"].append(elapsed_time)
            results["predictions"].append({
                "message": message,
                "expected": expected_intent,
                "predicted": predicted_intent,
                "correct": is_correct,
                "time": elapsed_time
            })
            
            print(f"  Expected: {expected_intent}, Predicted: {predicted_intent}")
            print(f"  {status} - Time: {elapsed_time:.2f}s")
            
        except Exception as e:
            print(f"  ✗ ERROR: {str(e)}")
    
    # Calculate statistics
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    
    accuracy = (results["correct"] / results["total"]) * 100
    avg_time = sum(results["times"]) / len(results["times"]) if results["times"] else 0
    min_time = min(results["times"]) if results["times"] else 0
    max_time = max(results["times"]) if results["times"] else 0
    
    print(f"\nModel: minimax-m2:cloud")
    print(f"  Initialization: {init_time:.2f}s")
    print(f"  Agent Creation: {agent_time:.2f}s")
    print(f"  Accuracy: {accuracy:.1f}% ({results['correct']}/{results['total']})")
    print(f"  Avg Inference Time: {avg_time:.2f}s")
    print(f"  Min Inference Time: {min_time:.2f}s")
    print(f"  Max Inference Time: {max_time:.2f}s")
    print(f"  Total Test Time: {sum(results['times']):.2f}s")
    
    # Show errors
    errors = [p for p in results["predictions"] if not p["correct"]]
    if errors:
        print(f"\n❌ Failed cases ({len(errors)}):")
        for err in errors:
            print(f"  - '{err['message']}'")
            print(f"    Expected: {err['expected']}, Got: {err['predicted']}")
    
    print("\n" + "="*80)
    
    # Save results
    import json
    with open("minimax_test_results.json", 'w', encoding='utf-8') as f:
        json.dump({
            "model": "minimax-m2:cloud",
            "init_time": init_time,
            "agent_time": agent_time,
            "accuracy": accuracy,
            "avg_time": avg_time,
            "min_time": min_time,
            "max_time": max_time,
            "predictions": results["predictions"]
        }, f, indent=2, ensure_ascii=False)
    
    print("📊 Detailed results saved to: minimax_test_results.json")


if __name__ == "__main__":
    asyncio.run(test_minimax())
