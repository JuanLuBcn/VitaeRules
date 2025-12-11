# Intent Detection: Critical Analysis & Strategy

## The Core Problem

### Intent Ambiguity Matrix

Let's map the REAL challenges:

```
┌─────────────────────────────────────────────────────────────────┐
│                    EASY TO CLASSIFY                             │
├─────────────────────────────────────────────────────────────────┤
│ MEMORY_STORE:                                                   │
│   "Guarda que...", "María me dijo...", "Apunta..."            │
│   → Clear trigger words                                         │
│   → Confidence: 95%+                                           │
├─────────────────────────────────────────────────────────────────┤
│ TASK_CREATE:                                                    │
│   "Recuérdame...", "No olvides...", "Tengo que..."            │
│   → Clear trigger words                                         │
│   → Confidence: 90%+                                           │
├─────────────────────────────────────────────────────────────────┤
│ LIST_ADD:                                                       │
│   "Añade leche", "Comprar pan"                                │
│   → Short, imperative                                          │
│   → Confidence: 70-85%                                         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    HARD TO CLASSIFY                             │
├─────────────────────────────────────────────────────────────────┤
│ MEMORY_QUERY vs CHAT:  ← THE MAIN PROBLEM                     │
│                                                                 │
│ "¿Qué me dijo María?"                                          │
│   → MEMORY_QUERY (search memories)                            │
│   → Expects: Retrieved information                             │
│                                                                 │
│ "¿Qué opinas de Barcelona?"                                    │
│   → CHAT (general conversation)                                │
│   → Expects: Opinion/discussion                                │
│                                                                 │
│ BUT... What about:                                             │
│                                                                 │
│ "¿Qué sabes de Barcelona?"                                     │
│   → Could be EITHER!                                           │
│   → If user stored info → MEMORY_QUERY                        │
│   → If asking generally → CHAT                                 │
│                                                                 │
│ "¿Cuándo es el cumpleaños de Juan?"                           │
│   → MEMORY_QUERY (if stored)                                  │
│   → But user expects: "I don't know" if not stored            │
│                                                                 │
│ "¿Por qué María se muda?"                                      │
│   → MEMORY_QUERY (context from memories)                      │
│   → But could be CHAT (asking for reasoning/opinion)          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Critical Issues with Current Design

### Issue 1: Questions are Inherently Ambiguous

**The Problem:**
```
"¿Qué X?" can be:
  - Asking for stored info (MEMORY_QUERY)
  - Asking for opinion (CHAT)
  - Asking for explanation (CHAT with memory context)
```

**Examples:**

| Question | Most Likely Intent | Why? |
|----------|-------------------|------|
| "¿Qué me dijo María?" | MEMORY_QUERY | "me dijo" = expects past info |
| "¿Qué piensas de María?" | CHAT | "piensas" = asking opinion |
| "¿Qué sabes de María?" | **AMBIGUOUS** | Could be either |
| "¿Qué es Barcelona?" | CHAT | General knowledge |
| "¿Qué hice ayer?" | MEMORY_QUERY | Personal timeline |
| "¿Qué debería hacer?" | CHAT | Asking advice |

**Root Cause:**
The same syntactic structure serves different pragmatic functions.

---

### Issue 2: Context Determines Intent

**Example Scenario:**

```
User has stored: "María se muda a Barcelona en marzo"

User asks: "¿Por qué María se muda?"

What should happen?
  Option A (MEMORY_QUERY): Search memories → "No tengo esa información"
  Option B (CHAT): Use context + LLM reasoning → "Quizás por trabajo o familia?"
  Option C (HYBRID): Search first, if nothing found → Chat with context
```

**The Issue:**
Intent depends on WHAT'S IN MEMORY, not just the question structure.

---

### Issue 3: User Expectations are Fuzzy

**User Mental Model:**

```
User thinks: "My bot knows everything I told it"

When they ask: "¿Qué sabes de María?"

They expect:
  1. Show what I told you (MEMORY_QUERY)
  2. If nothing, say "no sé" (don't make stuff up)
  3. BUT... if they ask "¿Qué piensas de X?" they WANT creative response
```

**The Challenge:**
We need to detect: "Are they asking for FACTS or OPINIONS?"

---

## Proposed Solution: Hybrid Intent Strategy

### Strategy 1: Use CHAT as Default + Search Injection

**Core Idea:**
- ALL questions go to CHAT by default
- CHAT agent ALWAYS searches memory first
- If relevant memories found → Include in context
- Let LLM decide how to use the context

**Flow:**

```
User: "¿Qué me dijo María?"
  ↓
IntentDetector: CHAT (fallback for all questions)
  ↓
ChatAgent:
  1. Search memory("María")
  2. Found: "María se muda a Barcelona en marzo"
  3. Prompt LLM:
     """
     User asks: "¿Qué me dijo María?"
     
     From memories:
     - María se muda a Barcelona en marzo (Oct 25)
     
     Respond based on the memories. If memories answer the question,
     present them. Don't add speculation.
     """
  4. LLM: "María te dijo que se muda a Barcelona en marzo"
```

**Pros:**
- ✅ Simple: One less intent to detect
- ✅ Flexible: Works for both factual and opinion questions
- ✅ Context-aware: Always has memory context
- ✅ No false negatives: Never misses relevant memories

**Cons:**
- ❌ Slower: Always does search (even for "¿Qué tal?")
- ❌ Less explicit: Mixing retrieval and generation
- ❌ Harder to debug: Can't tell if response came from memory or LLM
- ❌ Hallucination risk: LLM might mix memories with made-up info

---

### Strategy 2: Explicit MEMORY_QUERY + CHAT Fallback

**Core Idea:**
- Detect MEMORY_QUERY for explicit retrieval questions
- Use CHAT for everything else
- CHAT can still search if needed

**Intent Detection Rules:**

```python
MEMORY_QUERY triggers:
  - "¿Qué me dijo...?"        (asking for past statement)
  - "¿Qué hablamos de...?"    (asking for past conversation)
  - "¿Cuándo fue...?"         (asking for past event)
  - "¿Dónde está...?"         (asking for stored location)
  - "¿Quién es...?"           (asking for stored info about person)
  - "Busca..."                (explicit search command)
  - "¿Qué sabes de...?"       (asking for stored facts)
  - "¿Qué tengo en...?"       (asking for stored items/tasks)

CHAT triggers:
  - "¿Qué piensas de...?"     (asking opinion)
  - "¿Qué opinas de...?"      (asking opinion)
  - "¿Por qué...?"            (asking reasoning - may need context)
  - "¿Cómo...?"               (asking advice)
  - "¿Debería...?"            (asking advice)
  - Everything else (fallback)
```

**Flow for MEMORY_QUERY:**

```
User: "¿Qué me dijo María?"
  ↓
IntentDetector: MEMORY_QUERY (high confidence)
  ↓
SearchAgent:
  1. Search memory("María me dijo")
  2. Found: "María se muda a Barcelona en marzo"
  3. Return results
  ↓
Agent Zero synthesizes:
  "María te dijo que se muda a Barcelona en marzo"
```

**Flow for CHAT with context:**

```
User: "¿Qué opinas de Barcelona?"
  ↓
IntentDetector: CHAT (opinion question)
  ↓
ChatAgent:
  1. Search memory("Barcelona") → Found: "María se muda allí"
  2. Prompt:
     """
     User asks: "¿Qué opinas de Barcelona?"
     
     Context from their life:
     - Their friend María is moving to Barcelona in March
     
     Give your opinion naturally. Reference the context if relevant.
     """
  3. LLM: "Barcelona es increíble! Por cierto, María tendrá..."
```

**Pros:**
- ✅ Explicit: Clear when we're retrieving vs generating
- ✅ Faster: CHAT doesn't always search
- ✅ Debuggable: Can log retrieval vs generation separately
- ✅ Less hallucination: MEMORY_QUERY is pure retrieval

**Cons:**
- ❌ Classification errors: Might classify MEMORY_QUERY as CHAT
- ❌ More complex: Need to maintain trigger rules
- ❌ Brittle: New question patterns might break

---

### Strategy 3: Unified QUERY Intent + Mode Detection

**Core Idea:**
- Single QUERY intent for all questions
- Sub-classify into modes: FACTUAL vs GENERATIVE
- Agent decides how to respond

**Intent Detection:**

```python
QUERY intent with modes:

Mode: FACTUAL (expect stored answer)
  - "¿Qué me dijo...?"
  - "¿Cuándo...?"
  - "¿Dónde...?"
  - "¿Qué tengo...?"
  
Mode: GENERATIVE (expect reasoned answer)
  - "¿Qué piensas...?"
  - "¿Por qué...?"
  - "¿Cómo...?"
  
Mode: HYBRID (could be either)
  - "¿Qué sabes de...?" → Search first, if nothing → Generate
```

**Flow:**

```
User: "¿Qué sabes de María?"
  ↓
IntentDetector:
  {
    "intent": "QUERY",
    "mode": "HYBRID",
    "query": "María"
  }
  ↓
QueryAgent:
  1. Search memory("María")
  2. If found → Format as factual response
  3. If not found → Generate conversational response
  4. If mode=GENERATIVE → Always generate (use memories as context)
```

**Pros:**
- ✅ Flexible: Handles all question types
- ✅ Graceful degradation: Falls back naturally
- ✅ User-friendly: Always responds appropriately

**Cons:**
- ❌ Complex: Need to maintain mode rules
- ❌ Edge cases: Mode detection can fail
- ❌ Not intuitive: Harder to explain/debug

---

## My Recommendation: **Strategy 2 with Smart Fallback**

### Why Strategy 2?

1. **Clear Separation of Concerns**
   - MEMORY_QUERY = Pure retrieval (fast, accurate)
   - CHAT = Conversational AI (flexible, creative)
   
2. **Easy to Debug**
   - Can log: "Intent: MEMORY_QUERY → Found 3 results"
   - Can log: "Intent: CHAT → Generated response with context"
   
3. **Explainable to Users**
   - "I searched your memories and found..."
   - vs "Based on what I know about you..."
   
4. **Graceful Degradation**
   - MEMORY_QUERY finds nothing → "No tengo información sobre eso"
   - CHAT always works → "No sé mucho de eso, pero..."

### Enhanced Strategy 2: Smart Classification

**Key Insight: Use Question Structure + Verbs**

```python
MEMORY_QUERY_INDICATORS = {
    # Past tense (asking for stored info)
    "verbs": ["dijo", "contó", "mencionó", "habló", "hablamos", "fue"],
    
    # Possession (asking for owned data)
    "possession": ["mi", "mis", "tengo", "tenemos"],
    
    # Explicit retrieval
    "retrieval": ["busca", "encuentra", "muéstrame"],
    
    # Storage questions
    "storage": ["guardé", "anoté", "apunté"],
    
    # Temporal (personal timeline)
    "temporal": ["cuándo", "qué día", "qué hora"],
    
    # Location (personal places)
    "location": ["dónde", "en qué lugar"]
}

CHAT_INDICATORS = {
    # Opinion/reasoning
    "opinion": ["piensas", "opinas", "crees", "parece"],
    
    # Advice/recommendation
    "advice": ["debería", "recomiendas", "sugieres", "mejor"],
    
    # Explanation/reasoning
    "reasoning": ["por qué", "cómo es que", "razón"],
    
    # General knowledge
    "knowledge": ["qué es", "explica", "define"]
}

def classify_question(message):
    """
    Smart question classification.
    """
    
    # Check for explicit CHAT indicators
    for indicator in CHAT_INDICATORS.values():
        if any(word in message.lower() for word in indicator):
            return "CHAT"
    
    # Check for MEMORY_QUERY indicators
    memory_score = 0
    for indicator in MEMORY_QUERY_INDICATORS.values():
        if any(word in message.lower() for word in indicator):
            memory_score += 1
    
    if memory_score >= 1:
        return "MEMORY_QUERY"
    
    # Default: CHAT (safer fallback)
    return "CHAT"
```

---

## Handling Edge Cases

### Case 1: "¿Qué sabes de X?"

**Problem:** Ambiguous - could be asking for stored facts OR general knowledge

**Solution:**
```python
if question_starts_with("qué sabes de"):
    # Try MEMORY_QUERY first
    results = search_memory(entity)
    
    if results:
        return format_memory_results(results)
    else:
        # Fallback to CHAT
        return chat_agent.respond(
            message,
            context="User asked about {entity} but no memories found. "
                    "Respond naturally saying you don't have information about that."
        )
```

### Case 2: "¿Por qué X?"

**Problem:** Could be asking for reasoning from memories OR general reasoning

**Solution:**
```python
if question_starts_with("por qué"):
    # Check if asking about stored info
    if refers_to_memory(message):  # e.g., "¿Por qué María se muda?"
        # Search memories for context
        context = search_memory(extract_entities(message))
        
        # CHAT with context
        return chat_agent.respond(
            message,
            context=context,
            instruction="User is asking for reasoning. Use the memories as context, "
                       "but if reason isn't explicitly stated, you can infer."
        )
    else:
        # Pure CHAT
        return chat_agent.respond(message)
```

### Case 3: Question About Tasks/Lists

**Problem:** "¿Qué tengo mañana?" - is this MEMORY_QUERY or TASK_QUERY?

**Solution:**
```python
# Special case: Questions about owned data
if question_about_owned_data(message):
    # Determine data type
    if "tarea" in message or "hacer" in message:
        return "TASK_QUERY"
    elif "lista" in message or "comprar" in message:
        return "LIST_QUERY"
    else:
        return "MEMORY_QUERY"  # General owned data
```

---

## Improved Intent Detector Prompt

```python
INTENT_DETECTION_PROMPT = """Analiza el mensaje del usuario y clasifica su intención.

Usuario: "{message}"

INTENCIONES:

1. MEMORY_STORE - Quiere guardar información
   Indicadores: "guarda", "apunta", "me dijo", "anota"
   Ejemplo: "María me dijo que se muda a Barcelona"

2. MEMORY_QUERY - Quiere recuperar información guardada
   Indicadores: "me dijo", "hablamos", "fue", "tengo", "mis", "cuándo", "dónde"
   Ejemplo: "¿Qué me dijo María?", "¿Cuándo es mi reunión?"
   
   IMPORTANTE: Solo si pregunta por información PERSONAL/GUARDADA.
   NO para conocimiento general.

3. TASK_CREATE - Quiere crear recordatorio/tarea
   Indicadores: "recuérdame", "no olvides", "tengo que"
   Ejemplo: "Recuérdame llamar a Juan mañana"

4. LIST_ADD - Quiere añadir a una lista
   Indicadores: "añade", "comprar", "agregar", items cortos
   Ejemplo: "Añade leche a la compra"

5. CHAT - Conversación general, opiniones, consejos, conocimiento general
   Indicadores: "piensas", "opinas", "por qué", "qué es", "cómo"
   Ejemplo: "¿Qué opinas de Barcelona?", "¿Qué es el budismo?"
   
   IMPORTANTE: Si hay duda entre MEMORY_QUERY y CHAT → elige CHAT (fallback)

REGLAS DE DESAMBIGUACIÓN:

"¿Qué me dijo X?" → MEMORY_QUERY (pasado + personal)
"¿Qué piensas de X?" → CHAT (opinión)
"¿Qué sabes de X?" → CHAT (ambiguo, mejor fallback)
"¿Por qué X?" → CHAT (razonamiento, puede usar contexto)
"¿Cuándo X?" → MEMORY_QUERY si es personal, CHAT si es general

JSON:
{{
  "intent": "MEMORY_STORE | MEMORY_QUERY | TASK_CREATE | LIST_ADD | CHAT",
  "confidence": 0.0-1.0,
  "reasoning": "Por qué elegiste este intent",
  "entities": {{
    // Datos extraídos
  }}
}}

EJEMPLO:

Usuario: "¿Qué me dijo María sobre Barcelona?"
→ {{
  "intent": "MEMORY_QUERY",
  "confidence": 0.95,
  "reasoning": "Pregunta por información pasada ('me dijo') sobre conversación personal",
  "entities": {{
    "query": "María Barcelona",
    "people": ["María"],
    "topic": "Barcelona"
  }}
}}

Usuario: "¿Qué opinas de Barcelona?"
→ {{
  "intent": "CHAT",
  "confidence": 0.98,
  "reasoning": "Pregunta por opinión ('opinas'), no por información guardada",
  "entities": {{
    "topic": "Barcelona"
  }}
}}"""
```

---

## Testing Strategy

### Test Cases for Intent Detection

```python
TEST_CASES = [
    # Clear MEMORY_QUERY
    ("¿Qué me dijo María?", "MEMORY_QUERY", "> 0.9"),
    ("¿Cuándo es mi reunión?", "MEMORY_QUERY", "> 0.9"),
    ("¿Dónde guardé las llaves?", "MEMORY_QUERY", "> 0.85"),
    
    # Clear CHAT
    ("¿Qué opinas de Barcelona?", "CHAT", "> 0.9"),
    ("¿Por qué el cielo es azul?", "CHAT", "> 0.9"),
    ("¿Cómo estás?", "CHAT", "> 0.95"),
    
    # Ambiguous (should default to CHAT)
    ("¿Qué sabes de Barcelona?", "CHAT", "> 0.6"),
    ("¿Por qué María se muda?", "CHAT", "> 0.7"),
    
    # Clear TASK_CREATE
    ("Recuérdame llamar a Juan", "TASK_CREATE", "> 0.95"),
    
    # Clear MEMORY_STORE
    ("Guarda que María se muda", "MEMORY_STORE", "> 0.95"),
    
    # Clear LIST_ADD
    ("Añade leche", "LIST_ADD", "> 0.8"),
]

def test_intent_detection():
    """Run test suite on intent detector."""
    for message, expected_intent, expected_confidence in TEST_CASES:
        result = intent_detector.detect(message)
        
        assert result["intent"] == expected_intent, \
            f"Failed: {message} → {result['intent']} (expected {expected_intent})"
        
        assert eval(f"{result['confidence']} {expected_confidence}"), \
            f"Low confidence: {message} → {result['confidence']}"
        
        print(f"✅ {message} → {result['intent']} ({result['confidence']:.2f})")
```

---

## Implementation Roadmap

### Phase 1: Basic Intent Detection (This Week)
- [ ] Implement Strategy 2 (MEMORY_QUERY + CHAT fallback)
- [ ] Test on 20 example messages
- [ ] Measure accuracy (target: >85%)

### Phase 2: Smart Fallback (Next Week)
- [ ] Implement "try MEMORY_QUERY, fallback to CHAT" for ambiguous cases
- [ ] Add reasoning to responses ("I searched... but found nothing")
- [ ] Test edge cases

### Phase 3: Continuous Improvement (Ongoing)
- [ ] Log misclassifications
- [ ] Add new patterns based on real usage
- [ ] A/B test different strategies

---

## Critical Questions for You

### 1. **Fallback Strategy**
If MEMORY_QUERY finds nothing, should we:
- **Option A:** "No tengo información sobre eso" (explicit)
- **Option B:** Auto-fallback to CHAT (seamless)
- **Option C:** Ask user: "No encontré nada. ¿Quieres que te dé mi opinión?"

**My Recommendation:** Option B (seamless) with a hint:
```
"No tengo información guardada sobre eso. Pero te puedo decir que Barcelona..."
```

### 2. **Confidence Threshold**
If intent confidence < 0.7, should we:
- **Option A:** Default to CHAT (safe fallback)
- **Option B:** Ask user to clarify
- **Option C:** Execute best guess + mention uncertainty

**My Recommendation:** Option A (default to CHAT)

### 3. **Contextual Intent**
Should intent change based on conversation history?

Example:
```
User: "¿Qué me dijo María?"
Bot: "Que se muda a Barcelona"
User: "¿Por qué?" ← Does this mean "why she moves?" or "why did you say that?"
```

**My Recommendation:** Keep it simple for now. Treat each message independently.

---

## Final Verdict

**Use Strategy 2 (Explicit MEMORY_QUERY + CHAT Fallback) with these rules:**

1. ✅ **Default to CHAT when uncertain** (safer, more flexible)
2. ✅ **Explicit indicators for MEMORY_QUERY** (past tense, possession, retrieval verbs)
3. ✅ **CHAT always searches memory first** (provides context)
4. ✅ **Clear user communication** ("I searched...", "Based on what you told me...")
5. ✅ **Measure and iterate** (log misclassifications, improve prompts)

**The key insight:** Don't try to be perfect. Build a system that:
- Works well for clear cases (90% of messages)
- Degrades gracefully for ambiguous cases (10% of messages)
- Learns from mistakes (improve prompts based on logs)

What do you think? Should we go with Strategy 2, or do you prefer a different approach?
