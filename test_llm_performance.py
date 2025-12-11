"""
LLM Performance Test for Intent Classification

Tests different Ollama models on:
1. Intent classification accuracy (SEARCH vs ACTION)
2. Response time
3. Consistency across multiple runs

Models to test:
- gemma2:2b
- qwen2.5:1.5b
- llama3.2:3b
- deepseek-r1:1.5b

Note: minimax-m2:cloud is not available in Ollama (cloud service)
"""

import asyncio
import time
from typing import Dict, List, Tuple
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from crewai import Agent, Task, Crew, LLM


# Test cases with expected intent
TEST_CASES = [
    # SEARCH intent (questions)
    ("What is in my shopping list?", "SEARCH"),
    ("What did I do last Tuesday?", "SEARCH"),
    ("What is my cat's name?", "SEARCH"),
    ("When is my doctor appointment?", "SEARCH"),
    ("Do I have any tasks for today?", "SEARCH"),
    ("Who built the Sagrada Familia?", "SEARCH"),  # General knowledge
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


async def test_model(model_name: str, test_cases: List[Tuple[str, str]]) -> Dict:
    """Test a single model on all test cases."""
    print(f"\n{'='*60}")
    print(f"Testing model: {model_name}")
    print(f"{'='*60}")
    
    results = {
        "model": model_name,
        "correct": 0,
        "total": len(test_cases),
        "times": [],
        "predictions": [],
        "errors": []
    }
    
    try:
        # Create LLM instance directly
        llm = LLM(
            model=f"ollama/{model_name}",
            base_url="http://localhost:11434",
            temperature=0.7
        )
        
        # Test each case
        for i, (message, expected_intent) in enumerate(test_cases, 1):
            try:
                print(f"\n[{i}/{len(test_cases)}] Testing: '{message[:50]}...'")
                
                # Create agent and task
                agent = create_intent_agent(llm)
                task = create_intent_task(agent, message)
                
                # Create crew and execute
                crew = Crew(
                    agents=[agent],
                    tasks=[task],
                    verbose=False
                )
                
                # Measure time
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
                    # Try to find SEARCH or ACTION anywhere in output
                    if "SEARCH" in output_upper and "ACTION" not in output_upper:
                        predicted_intent = "SEARCH"
                    else:
                        predicted_intent = "ACTION"  # Default
                
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
                
                print(f"  Expected: {expected_intent}, Predicted: {predicted_intent} - {status} ({elapsed_time:.2f}s)")
                
            except Exception as e:
                print(f"  ✗ ERROR: {str(e)}")
                results["errors"].append({
                    "message": message,
                    "error": str(e)
                })
        
        # Calculate statistics
        accuracy = (results["correct"] / results["total"]) * 100
        avg_time = sum(results["times"]) / len(results["times"]) if results["times"] else 0
        min_time = min(results["times"]) if results["times"] else 0
        max_time = max(results["times"]) if results["times"] else 0
        
        results["accuracy"] = accuracy
        results["avg_time"] = avg_time
        results["min_time"] = min_time
        results["max_time"] = max_time
        
        print(f"\n{'='*60}")
        print(f"Results for {model_name}:")
        print(f"  Accuracy: {accuracy:.1f}% ({results['correct']}/{results['total']})")
        print(f"  Avg Time: {avg_time:.2f}s")
        print(f"  Min Time: {min_time:.2f}s")
        print(f"  Max Time: {max_time:.2f}s")
        print(f"  Errors: {len(results['errors'])}")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"\n✗ FAILED TO TEST {model_name}: {str(e)}")
        results["error"] = str(e)
    
    return results


def print_summary(all_results: List[Dict]):
    """Print summary comparison table."""
    print(f"\n\n{'='*80}")
    print("SUMMARY - LLM COMPARISON")
    print(f"{'='*80}\n")
    
    # Header
    print(f"{'Model':<20} {'Accuracy':<12} {'Avg Time':<12} {'Min Time':<12} {'Max Time':<12}")
    print(f"{'-'*80}")
    
    # Sort by accuracy (descending)
    sorted_results = sorted(
        [r for r in all_results if "accuracy" in r],
        key=lambda x: x["accuracy"],
        reverse=True
    )
    
    for result in sorted_results:
        print(f"{result['model']:<20} "
              f"{result['accuracy']:>6.1f}%     "
              f"{result['avg_time']:>6.2f}s      "
              f"{result['min_time']:>6.2f}s      "
              f"{result['max_time']:>6.2f}s")
    
    print(f"{'-'*80}\n")
    
    # Best model
    if sorted_results:
        best = sorted_results[0]
        print(f"🏆 BEST ACCURACY: {best['model']} ({best['accuracy']:.1f}%)")
        
        fastest = min(sorted_results, key=lambda x: x['avg_time'])
        print(f"⚡ FASTEST: {fastest['model']} ({fastest['avg_time']:.2f}s avg)")
        
        # Best balance (accuracy * speed score)
        for r in sorted_results:
            # Lower time is better, so invert for scoring
            time_score = 1 / r['avg_time'] if r['avg_time'] > 0 else 0
            r['balance_score'] = r['accuracy'] * time_score
        
        best_balance = max(sorted_results, key=lambda x: x['balance_score'])
        print(f"⚖️  BEST BALANCE: {best_balance['model']} "
              f"(accuracy: {best_balance['accuracy']:.1f}%, time: {best_balance['avg_time']:.2f}s)")
    
    print(f"\n{'='*80}")


async def main():
    """Main test execution."""
    print("="*80)
    print("LLM INTENT CLASSIFICATION PERFORMANCE TEST")
    print("="*80)
    print(f"\nTest cases: {len(TEST_CASES)}")
    print(f"  - SEARCH intent: {sum(1 for _, intent in TEST_CASES if intent == 'SEARCH')}")
    print(f"  - ACTION intent: {sum(1 for _, intent in TEST_CASES if intent == 'ACTION')}")
    
    # Models to test (from available Ollama models)
    models = [
        "llama3.2:1b",         # 1.3 GB - Smallest Llama
        "qwen3:1.7b",          # 1.4 GB - Small, fast
        "deepseek-r1:1.5b",    # 1.1 GB - Reasoning-focused
        "llama3.2:3b",         # 2.0 GB - Currently used in app (baseline)
        "gemma3:4b",           # 3.3 GB - Newer Gemma model
        "qwen3:8b",            # 5.2 GB - Larger Qwen
        "minimax-m2:cloud"     # Cloud model (via Ollama proxy)
    ]
    
    print(f"\nModels to test: {', '.join(models)}")
    print("\nNote: Make sure these models are pulled in Ollama:")
    for model in models:
        print(f"  ollama pull {model}")
    
    input("\nPress Enter to start testing...")
    
    # Test all models
    all_results = []
    for model in models:
        result = await test_model(model, TEST_CASES)
        all_results.append(result)
        
        # Small delay between models
        await asyncio.sleep(2)
    
    # Print summary
    print_summary(all_results)
    
    # Save detailed results
    import json
    output_file = "llm_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 Detailed results saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
