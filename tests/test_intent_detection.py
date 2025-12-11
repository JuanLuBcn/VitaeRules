"""
Intent Detection Performance Test

Tests the LLM's ability to classify user messages into intents
WITHOUT relying on keyword matching - pure semantic understanding.

Run this to validate strategy before implementing full Agent Zero.
"""

import asyncio
import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.llm import LLMService


# Test dataset with expected intents
TEST_CASES = [
    # ===== MEMORY_STORE (Clear cases) =====
    {
        "message": "María me dijo que se muda a Barcelona en marzo",
        "expected": "MEMORY_STORE",
        "confidence_threshold": 0.85,
        "category": "store_clear"
    },
    {
        "message": "Guarda que a Juan le gusta el fútbol",
        "expected": "MEMORY_STORE",
        "confidence_threshold": 0.90,
        "category": "store_clear"
    },
    {
        "message": "Apunta: reunión con el cliente el viernes",
        "expected": "MEMORY_STORE",
        "confidence_threshold": 0.85,
        "category": "store_clear"
    },
    {
        "message": "No olvides que Pedro es vegetariano",
        "expected": "MEMORY_STORE",
        "confidence_threshold": 0.80,
        "category": "store_clear"
    },
    
    # ===== MEMORY_QUERY (Clear cases) =====
    {
        "message": "¿Qué me dijo María?",
        "expected": "MEMORY_QUERY",
        "confidence_threshold": 0.90,
        "category": "query_clear"
    },
    {
        "message": "¿Cuándo es mi reunión con el cliente?",
        "expected": "MEMORY_QUERY",
        "confidence_threshold": 0.85,
        "category": "query_clear"
    },
    {
        "message": "¿Dónde guardé las llaves?",
        "expected": "MEMORY_QUERY",
        "confidence_threshold": 0.80,
        "category": "query_clear"
    },
    {
        "message": "¿Qué hablamos María y yo la semana pasada?",
        "expected": "MEMORY_QUERY",
        "confidence_threshold": 0.85,
        "category": "query_clear"
    },
    {
        "message": "Busca información sobre el proyecto X",
        "expected": "MEMORY_QUERY",
        "confidence_threshold": 0.85,
        "category": "query_clear"
    },
    
    # ===== CHAT (Clear cases) =====
    {
        "message": "¿Qué opinas de Barcelona?",
        "expected": "CHAT",
        "confidence_threshold": 0.90,
        "category": "chat_clear"
    },
    {
        "message": "¿Qué piensas sobre la inteligencia artificial?",
        "expected": "CHAT",
        "confidence_threshold": 0.90,
        "category": "chat_clear"
    },
    {
        "message": "¿Cómo estás?",
        "expected": "CHAT",
        "confidence_threshold": 0.95,
        "category": "chat_clear"
    },
    {
        "message": "¿Qué es el budismo?",
        "expected": "CHAT",
        "confidence_threshold": 0.90,
        "category": "chat_clear"
    },
    {
        "message": "¿Por qué el cielo es azul?",
        "expected": "CHAT",
        "confidence_threshold": 0.90,
        "category": "chat_clear"
    },
    {
        "message": "Cuéntame un chiste",
        "expected": "CHAT",
        "confidence_threshold": 0.95,
        "category": "chat_clear"
    },
    
    # ===== TASK_CREATE (Clear cases) =====
    {
        "message": "Recuérdame llamar a Juan mañana",
        "expected": "TASK_CREATE",
        "confidence_threshold": 0.95,
        "category": "task_clear"
    },
    {
        "message": "Tengo que enviar el reporte el viernes",
        "expected": "TASK_CREATE",
        "confidence_threshold": 0.80,
        "category": "task_clear"
    },
    {
        "message": "No olvides comprar flores para mamá",
        "expected": "TASK_CREATE",
        "confidence_threshold": 0.85,
        "category": "task_clear"
    },
    
    # ===== LIST_ADD (Clear cases) =====
    {
        "message": "Añade leche a la lista de compras",
        "expected": "LIST_ADD",
        "confidence_threshold": 0.90,
        "category": "list_clear"
    },
    {
        "message": "Comprar pan y huevos",
        "expected": "LIST_ADD",
        "confidence_threshold": 0.75,
        "category": "list_clear"
    },
    {
        "message": "Leche",
        "expected": "LIST_ADD",
        "confidence_threshold": 0.60,  # Lower - very ambiguous
        "category": "list_ambiguous"
    },
    
    # ===== AMBIGUOUS CASES (The real challenge!) =====
    {
        "message": "¿Qué sabes de Barcelona?",
        "expected": "CHAT",  # Could be MEMORY_QUERY, but default to CHAT
        "confidence_threshold": 0.50,  # Lower expectation - truly ambiguous
        "category": "ambiguous",
        "notes": "Could be asking for memories OR general knowledge. CHAT is safer fallback."
    },
    {
        "message": "¿Por qué María se muda?",
        "expected": "CHAT",  # Asking for reasoning, even if context exists
        "confidence_threshold": 0.60,
        "category": "ambiguous",
        "notes": "Asking WHY (reasoning) not WHAT (facts). CHAT can use memory as context."
    },
    {
        "message": "¿Qué sabes de Juan?",
        "expected": "CHAT",  # Ambiguous, prefer CHAT fallback
        "confidence_threshold": 0.50,
        "category": "ambiguous",
        "notes": "Could want stored info OR general chat. Let CHAT search memory."
    },
    {
        "message": "Háblame de María",
        "expected": "MEMORY_QUERY",  # More like asking for info
        "confidence_threshold": 0.65,
        "category": "ambiguous",
        "notes": "Asking for information, more likely wants stored facts."
    },
    
    # ===== COMPOSITE (Multiple intents) =====
    {
        "message": "Recuérdame llamar a Juan mañana y guarda que le gusta el fútbol",
        "expected": "COMPOSITE",
        "confidence_threshold": 0.80,
        "category": "composite"
    },
    {
        "message": "Añade pan a la compra y recuérdame ir al super",
        "expected": "COMPOSITE",
        "confidence_threshold": 0.75,
        "category": "composite"
    },
]


# Intent detection prompt (Strategy 2)
INTENT_DETECTION_SYSTEM = """Eres un clasificador de intenciones para un asistente personal.
Analiza el mensaje del usuario y determina qué quiere hacer.

Responde SIEMPRE con JSON válido, sin markdown ni explicaciones adicionales."""


def build_intent_prompt(message: str) -> str:
    """Build the intent detection prompt - SEMANTIC ONLY, no keywords or examples."""
    
    return f"""Analiza el significado semántico de este mensaje:

"{message}"

Clasifica la INTENCIÓN del usuario en UNA de estas categorías según su propósito comunicativo:

1. MEMORY_STORE
   El usuario está AFIRMANDO información nueva que quiere que recuerdes.
   Está INFORMANDO sobre hechos, eventos, o características de personas/cosas.
   Propósito: Almacenar conocimiento para uso futuro.

2. MEMORY_QUERY  
   El usuario está PREGUNTANDO por información que previamente te ha contado.
   Está buscando RECUPERAR conocimiento personal o eventos pasados de su vida.
   Propósito: Consultar memoria personal almacenada.

3. TASK_CREATE
   El usuario quiere establecer un RECORDATORIO o compromiso FUTURO.
   Está delegando la responsabilidad de recordarle algo en un momento específico.
   Propósito: Crear recordatorio temporal de una acción futura.

4. LIST_ADD
   El usuario quiere AGREGAR elementos a una colección categorizada.
   Está gestionando items agrupados por contexto (compras, tareas, etc).
   Propósito: Añadir a una lista existente o nueva.

5. CHAT
   El usuario busca CONVERSACIÓN, opiniones, consejos, o conocimiento GENERAL.
   Está solicitando razonamiento, análisis, o información que NO ha almacenado.
   Propósito: Interacción conversacional abierta.
   
   NOTA IMPORTANTE: En caso de AMBIGÜEDAD entre MEMORY_QUERY y CHAT, 
   elige CHAT (es más seguro como fallback).

6. COMPOSITE
   El mensaje contiene DOS O MÁS intenciones distintas que deben ejecutarse.
   Propósito: Múltiples acciones en un solo mensaje.

PRINCIPIO CLAVE DE DESAMBIGUACIÓN:

Pregúntate:
- ¿Está AFIRMANDO algo nuevo? → MEMORY_STORE
- ¿Está PREGUNTANDO por algo QUE ÉL/ELLA te contó? → MEMORY_QUERY
- ¿Está PREGUNTANDO por opinión/conocimiento general? → CHAT
- ¿Está pidiendo un RECORDATORIO futuro? → TASK_CREATE
- ¿Está AÑADIENDO a una colección? → LIST_ADD
- ¿Hay MÚLTIPLES intenciones? → COMPOSITE

Si NO ESTÁS SEGURO → elige CHAT (fallback seguro)

Responde SOLO con JSON válido:

{{
  "intent": "MEMORY_STORE | MEMORY_QUERY | TASK_CREATE | LIST_ADD | CHAT | COMPOSITE",
  "confidence": 0.0-1.0,
  "reasoning": "Explicación breve del razonamiento semántico",
  "entities": {{}}
}}"""


async def test_intent_detection():
    """Run intent detection tests."""
    
    print("=" * 80)
    print("INTENT DETECTION PERFORMANCE TEST")
    print("=" * 80)
    print()
    
    # Initialize LLM
    llm = LLMService()
    
    # Results tracking
    results = {
        "total": 0,
        "correct": 0,
        "incorrect": 0,
        "low_confidence": 0,
        "by_category": {},
        "failures": []
    }
    
    # Run tests
    for i, test_case in enumerate(TEST_CASES, 1):
        message = test_case["message"]
        expected = test_case["expected"]
        threshold = test_case["confidence_threshold"]
        category = test_case["category"]
        
        print(f"\n[Test {i}/{len(TEST_CASES)}] Category: {category}")
        print(f"Message: \"{message}\"")
        print(f"Expected: {expected} (confidence ≥ {threshold})")
        
        # Detect intent
        try:
            prompt = build_intent_prompt(message)
            result = llm.generate_json(prompt, INTENT_DETECTION_SYSTEM)
            
            detected = result.get("intent", "UNKNOWN")
            confidence = result.get("confidence", 0.0)
            reasoning = result.get("reasoning", "")
            
            # Check correctness
            is_correct = detected == expected
            is_confident = confidence >= threshold
            
            # Update results
            results["total"] += 1
            
            if is_correct:
                results["correct"] += 1
                status = "✅ PASS"
            else:
                results["incorrect"] += 1
                status = "❌ FAIL"
                results["failures"].append({
                    "message": message,
                    "expected": expected,
                    "detected": detected,
                    "confidence": confidence,
                    "category": category
                })
            
            if not is_confident:
                results["low_confidence"] += 1
                status += " ⚠️ LOW CONFIDENCE"
            
            # Track by category
            if category not in results["by_category"]:
                results["by_category"][category] = {
                    "total": 0, "correct": 0
                }
            results["by_category"][category]["total"] += 1
            if is_correct:
                results["by_category"][category]["correct"] += 1
            
            print(f"Detected: {detected} (confidence: {confidence:.2f}) {status}")
            print(f"Reasoning: {reasoning}")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            results["total"] += 1
            results["incorrect"] += 1
            results["failures"].append({
                "message": message,
                "expected": expected,
                "detected": "ERROR",
                "error": str(e),
                "category": category
            })
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    accuracy = (results["correct"] / results["total"] * 100) if results["total"] > 0 else 0
    
    print(f"\nOverall Performance:")
    print(f"  Total tests: {results['total']}")
    print(f"  Correct: {results['correct']} ({accuracy:.1f}%)")
    print(f"  Incorrect: {results['incorrect']}")
    print(f"  Low confidence: {results['low_confidence']}")
    
    print(f"\nPerformance by Category:")
    for category, stats in sorted(results["by_category"].items()):
        cat_accuracy = (stats["correct"] / stats["total"] * 100) if stats["total"] > 0 else 0
        status = "✅" if cat_accuracy >= 80 else "⚠️" if cat_accuracy >= 60 else "❌"
        print(f"  {status} {category:20s}: {stats['correct']}/{stats['total']} ({cat_accuracy:.1f}%)")
    
    if results["failures"]:
        print(f"\nFailures ({len(results['failures'])}):")
        for failure in results["failures"]:
            print(f"\n  Message: \"{failure['message']}\"")
            print(f"  Expected: {failure['expected']}")
            print(f"  Detected: {failure.get('detected', 'ERROR')}")
            if 'confidence' in failure:
                print(f"  Confidence: {failure['confidence']:.2f}")
            if 'error' in failure:
                print(f"  Error: {failure['error']}")
            print(f"  Category: {failure['category']}")
    
    # Final assessment
    print("\n" + "=" * 80)
    print("ASSESSMENT")
    print("=" * 80)
    
    if accuracy >= 85:
        print("✅ EXCELLENT - Intent detection is production-ready!")
    elif accuracy >= 75:
        print("⚠️  GOOD - Intent detection works but needs prompt refinement")
    elif accuracy >= 60:
        print("⚠️  FAIR - Significant prompt improvements needed")
    else:
        print("❌ POOR - Need to reconsider strategy or use better model")
    
    print(f"\nTarget: ≥85% accuracy")
    print(f"Current: {accuracy:.1f}%")
    
    # Save results
    output_file = Path("data/intent_detection_test_results.json")
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Results saved to: {output_file}")
    
    return results


if __name__ == "__main__":
    asyncio.run(test_intent_detection())
