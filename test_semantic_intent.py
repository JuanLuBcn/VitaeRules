"""
Test semantic intent detection after removing examples and keywords.

This tests that the LLM can still correctly classify intents based purely
on semantic understanding, without relying on keyword matching or examples.
"""

import asyncio
import time
from crewai import Agent, Task, Crew, LLM


# Test cases designed to test semantic understanding (no obvious keywords)
TEST_CASES = [
    # SEARCH - phrased without obvious question words
    ("Cuéntame sobre mi lista de compras", "SEARCH"),  # Tell me about (not "what is")
    ("Me gustaría saber qué hice el martes pasado", "SEARCH"),  # I'd like to know
    ("Necesito información sobre mis tareas pendientes", "SEARCH"),  # Need info
    ("Dime el nombre de mi gato", "SEARCH"),  # Tell me (command form)
    
    # SEARCH - with obvious question words (should still work)
    ("¿Qué hay en mi lista?", "SEARCH"),
    ("¿Cuándo es mi cita?", "SEARCH"),
    
    # ACTION - statements without command words
    ("Hoy vi a Jorge en el parque", "ACTION"),  # Statement
    ("Estuve en la oficina con Biel", "ACTION"),  # Past event
    ("Mi gata se llama Luna y tiene 3 años", "ACTION"),  # Information
    
    # ACTION - with command-like structure
    ("Pon tomates en la lista", "ACTION"),  # Command
    ("Necesito recordar llamar al doctor", "ACTION"),  # "Need to remember"
    
    # ACTION - social/expressive
    ("Hola!", "ACTION"),
    ("Gracias por tu ayuda", "ACTION"),
    ("Me siento cansado hoy", "ACTION"),
    
    # Tricky cases - semantic understanding required
    ("¿Me puedes ayudar?", "SEARCH"),  # Asking for capabilities
    ("Ayúdame con esto", "ACTION"),  # Command to help (not asking what help available)
    ("Ayer compré manzanas", "ACTION"),  # Past tense statement
    ("¿Compré manzanas ayer?", "SEARCH"),  # Question about past
]


def create_intent_agent(llm) -> Agent:
    """Create intent analyzer agent with semantic backstory."""
    return Agent(
        role="Intent Analyzer",
        goal="Analyze user messages to determine their intent: information retrieval or action execution",
        backstory="""You are an expert at understanding the fundamental intent behind user messages. 
        You analyze what users truly want to accomplish by examining the semantic meaning 
        of their communication, not just surface-level patterns.

        You distinguish between two primary intents:

        **SEARCH**: The user seeks information they don't currently have. They are asking 
        a question that requires retrieving data from memory, tasks, lists, or general knowledge. 
        The core intent is to receive an answer.

        **ACTION**: The user wants to store information, execute a command, express themselves, 
        or engage in communication. This includes providing new information, sharing experiences, 
        giving instructions, or social interaction. The core intent is to communicate or record 
        something, not to retrieve information.

        You focus on understanding what the user fundamentally wants to achieve, 
        considering conversation context and the natural flow of dialogue. 
        You default to ACTION when intent is ambiguous, ensuring valuable information isn't lost.""",
        verbose=False,
        allow_delegation=False,
        llm=llm
    )


def create_intent_task(agent: Agent, message: str) -> Task:
    """Create intent classification task with semantic prompt (no examples)."""
    return Task(
        description=f"""Analyze this user message and determine the user's primary intent:

User message: "{message}"

Recent conversation history:
No previous messages

Classify the intent as ONE of these TWO categories based on semantic meaning:

**SEARCH**: The user wants to retrieve or query existing information
- Requesting information from stored data
- Asking about past events, conversations, or memories
- Inquiring about general knowledge
- The message is a question seeking an answer

**ACTION**: The user wants to store, create, modify, or communicate information (DEFAULT)
- Providing new information or describing events
- Giving commands to store, modify, or delete data
- Engaging in social interaction
- Sharing thoughts, feelings, or observations
- Any message that is NOT explicitly requesting information
- When uncertain, choose ACTION

Understand what the user fundamentally wants to accomplish:
- ASKING for information they don't have → SEARCH
- TELLING you something or expressing themselves → ACTION

Default to ACTION unless the message is clearly seeking information.

Output format:
Primary Intent: [SEARCH/ACTION]
Reasoning: [Brief explanation of your decision based on semantic analysis]""",
        agent=agent,
        expected_output="Intent classification (SEARCH or ACTION) with reasoning"
    )


async def test_semantic_intent():
    """Test semantic intent detection without examples/keywords."""
    print("="*80)
    print("SEMANTIC INTENT DETECTION TEST")
    print("(No examples or keywords - pure semantic understanding)")
    print("="*80)
    
    # Create LLM
    llm = LLM(
        model="ollama/minimax-m2:cloud",
        base_url="http://localhost:11434",
        temperature=0.7
    )
    
    # Create agent (reuse for all tests)
    agent = create_intent_agent(llm)
    
    results = {
        "correct": 0,
        "total": len(TEST_CASES),
        "times": [],
        "predictions": []
    }
    
    for i, (message, expected_intent) in enumerate(TEST_CASES, 1):
        try:
            print(f"\n[{i}/{len(TEST_CASES)}] Testing: '{message}'")
            print(f"  Expected: {expected_intent}")
            
            # Create task
            task = create_intent_task(agent, message)
            
            # Create crew
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
                "time": elapsed_time,
                "reasoning": output
            })
            
            print(f"  Predicted: {predicted_intent} - {status} ({elapsed_time:.2f}s)")
            
        except Exception as e:
            print(f"  ✗ ERROR: {str(e)}")
    
    # Calculate statistics
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    
    accuracy = (results["correct"] / results["total"]) * 100
    avg_time = sum(results["times"]) / len(results["times"]) if results["times"] else 0
    
    print(f"\nModel: minimax-m2:cloud")
    print(f"Prompt Style: Semantic only (no examples, no keywords)")
    print(f"Accuracy: {accuracy:.1f}% ({results['correct']}/{results['total']})")
    print(f"Avg Time: {avg_time:.2f}s")
    
    # Show errors
    errors = [p for p in results["predictions"] if not p["correct"]]
    if errors:
        print(f"\n❌ Failed cases ({len(errors)}):")
        for err in errors:
            print(f"\n  Message: '{err['message']}'")
            print(f"  Expected: {err['expected']}, Got: {err['predicted']}")
            print(f"  Reasoning: {err['reasoning'][:200]}...")
    else:
        print("\n✅ All test cases passed!")
    
    print("\n" + "="*80)
    
    # Save results
    import json
    with open("semantic_intent_test_results.json", 'w', encoding='utf-8') as f:
        json.dump({
            "model": "minimax-m2:cloud",
            "prompt_style": "semantic_only_no_examples",
            "accuracy": accuracy,
            "avg_time": avg_time,
            "predictions": results["predictions"]
        }, f, indent=2, ensure_ascii=False)
    
    print("📊 Detailed results saved to: semantic_intent_test_results.json")
    
    return accuracy >= 85  # Pass if 85% or higher


if __name__ == "__main__":
    success = asyncio.run(test_semantic_intent())
    exit(0 if success else 1)
