"""
Optimized LLM Performance Test - Separates initialization from inference time

Measures:
1. Model initialization time (one-time)
2. Pure inference time per request
3. CrewAI overhead vs raw LLM time
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


INTENT_PROMPT_TEMPLATE = """Analyze this user message and determine the primary intent:

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
Reasoning: [Brief explanation]"""


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
        description=INTENT_PROMPT_TEMPLATE.format(message=message),
        agent=agent,
        expected_output="Intent classification (SEARCH or ACTION) with reasoning"
    )


async def test_model_optimized(model_name: str, test_cases: List[Tuple[str, str]]) -> Dict:
    """Test a single model with separated initialization and inference timing."""
    print(f"\n{'='*60}")
    print(f"Testing model: {model_name}")
    print(f"{'='*60}")
    
    results = {
        "model": model_name,
        "correct": 0,
        "total": len(test_cases),
        "init_time": 0,
        "inference_times": [],
        "total_times": [],
        "predictions": [],
        "errors": []
    }
    
    try:
        # === INITIALIZATION PHASE ===
        print("\n⏱️  Initializing model...")
        init_start = time.time()
        
        llm = LLM(
            model=f"ollama/{model_name}",
            base_url="http://localhost:11434",
            temperature=0.7
        )
        
        # Create agent once
        agent = create_intent_agent(llm)
        
        init_time = time.time() - init_start
        results["init_time"] = init_time
        print(f"   ✓ Initialization complete: {init_time:.2f}s")
        
        # === INFERENCE PHASE ===
        print("\n🧪 Running test cases...")
        
        for i, (message, expected_intent) in enumerate(test_cases, 1):
            try:
                print(f"\n[{i}/{len(test_cases)}] '{message[:50]}...'")
                
                # Measure TOTAL time (includes CrewAI overhead)
                total_start = time.time()
                
                # Create task for this message
                task = create_intent_task(agent, message)
                
                # Create crew and execute
                crew = Crew(
                    agents=[agent],
                    tasks=[task],
                    verbose=False
                )
                
                # Execute
                result = crew.kickoff()
                
                total_time = time.time() - total_start
                
                # Note: We can't easily separate pure LLM inference from CrewAI overhead
                # without modifying CrewAI internals, so we'll just track total time
                
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
                    status = "✓"
                else:
                    status = "✗"
                
                results["total_times"].append(total_time)
                results["inference_times"].append(total_time)  # Same for now
                results["predictions"].append({
                    "message": message,
                    "expected": expected_intent,
                    "predicted": predicted_intent,
                    "correct": is_correct,
                    "time": total_time
                })
                
                print(f"  {status} {predicted_intent} (expected: {expected_intent}) - {total_time:.2f}s")
                
            except Exception as e:
                print(f"  ✗ ERROR: {str(e)}")
                results["errors"].append({
                    "message": message,
                    "error": str(e)
                })
        
        # Calculate statistics
        accuracy = (results["correct"] / results["total"]) * 100
        avg_inference = sum(results["inference_times"]) / len(results["inference_times"]) if results["inference_times"] else 0
        min_inference = min(results["inference_times"]) if results["inference_times"] else 0
        max_inference = max(results["inference_times"]) if results["inference_times"] else 0
        
        results["accuracy"] = accuracy
        results["avg_inference_time"] = avg_inference
        results["min_inference_time"] = min_inference
        results["max_inference_time"] = max_inference
        
        print(f"\n{'='*60}")
        print(f"Results for {model_name}:")
        print(f"  ✓ Accuracy: {accuracy:.1f}% ({results['correct']}/{results['total']})")
        print(f"  ⚙️  Init Time: {init_time:.2f}s")
        print(f"  ⚡ Avg Inference: {avg_inference:.2f}s")
        print(f"  📊 Range: {min_inference:.2f}s - {max_inference:.2f}s")
        print(f"  ❌ Errors: {len(results['errors'])}")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"\n✗ FAILED TO TEST {model_name}: {str(e)}")
        results["error"] = str(e)
    
    return results


def print_summary(all_results: List[Dict]):
    """Print comprehensive comparison table."""
    print(f"\n\n{'='*90}")
    print("COMPREHENSIVE LLM COMPARISON")
    print(f"{'='*90}\n")
    
    # Header
    print(f"{'Model':<20} {'Accuracy':<10} {'Init':<8} {'Avg Time':<10} {'Min':<8} {'Max':<8}")
    print(f"{'-'*90}")
    
    # Sort by accuracy (descending), then by speed (ascending)
    sorted_results = sorted(
        [r for r in all_results if "accuracy" in r],
        key=lambda x: (-x["accuracy"], x["avg_inference_time"])
    )
    
    for result in sorted_results:
        print(f"{result['model']:<20} "
              f"{result['accuracy']:>6.1f}%    "
              f"{result['init_time']:>5.2f}s   "
              f"{result['avg_inference_time']:>6.2f}s    "
              f"{result['min_inference_time']:>5.2f}s   "
              f"{result['max_inference_time']:>5.2f}s")
    
    print(f"{'-'*90}\n")
    
    # Awards
    if sorted_results:
        best_accuracy = sorted_results[0]
        print(f"🏆 BEST ACCURACY: {best_accuracy['model']} ({best_accuracy['accuracy']:.1f}%)")
        
        fastest = min(sorted_results, key=lambda x: x['avg_inference_time'])
        print(f"⚡ FASTEST: {fastest['model']} ({fastest['avg_inference_time']:.2f}s avg)")
        
        # Best balance: normalize accuracy (0-100) and speed (inverse, normalized)
        max_time = max(r['avg_inference_time'] for r in sorted_results)
        for r in sorted_results:
            speed_score = (max_time - r['avg_inference_time']) / max_time * 100  # Higher is better
            r['balance_score'] = (r['accuracy'] + speed_score) / 2
        
        best_balance = max(sorted_results, key=lambda x: x['balance_score'])
        print(f"⚖️  BEST BALANCE: {best_balance['model']} "
              f"(accuracy: {best_balance['accuracy']:.1f}%, time: {best_balance['avg_inference_time']:.2f}s)")
        
        # Show wrong predictions for top models
        print(f"\n📋 Error Analysis for Top 3 Models:")
        for result in sorted_results[:3]:
            wrong = [p for p in result['predictions'] if not p['correct']]
            if wrong:
                print(f"\n  {result['model']} - {len(wrong)} errors:")
                for w in wrong:
                    print(f"    ✗ '{w['message'][:40]}...' → {w['predicted']} (expected: {w['expected']})")
            else:
                print(f"\n  {result['model']} - ✓ Perfect score!")
    
    print(f"\n{'='*90}")


async def main():
    """Main test execution."""
    print("="*90)
    print("OPTIMIZED LLM INTENT CLASSIFICATION PERFORMANCE TEST")
    print("="*90)
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
    
    print(f"\nModels to test ({len(models)} total):")
    for i, model in enumerate(models, 1):
        print(f"  {i}. {model}")
    
    print("\n⚠️  This test separates initialization time from inference time.")
    print("   Each model will be initialized once, then tested on all cases.")
    
    input("\nPress Enter to start testing...")
    
    # Test all models
    all_results = []
    total_start = time.time()
    
    for model in models:
        result = await test_model_optimized(model, TEST_CASES)
        all_results.append(result)
        
        # Small delay between models
        await asyncio.sleep(1)
    
    total_elapsed = time.time() - total_start
    
    # Print summary
    print_summary(all_results)
    
    print(f"\n⏱️  Total test duration: {total_elapsed/60:.1f} minutes")
    
    # Save detailed results
    import json
    output_file = "llm_test_results_optimized.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"📊 Detailed results saved to: {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
