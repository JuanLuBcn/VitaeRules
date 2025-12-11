# Phase 2: Smart Enrichment Agent - Architecture

**Date**: October 26, 2025  
**Status**: IN PROGRESS  
**Project**: Vitti Enhancement - Phase 2

## Overview

The **EnrichmentAgent** is a conversational AI component that intelligently asks follow-up questions to gather missing information about lists, tasks, and notes. It enables a natural, multi-turn conversation flow where Vitti proactively helps users provide richer context.

## Design Principles

1. **Natural Conversations**: Questions feel helpful, not like a form to fill
2. **Context-Aware**: Only asks about truly missing/valuable information
3. **Progressive Enhancement**: Works with or without enrichment
4. **User Control**: Users can skip enrichment or complete it later
5. **Spanish-First**: All prompts and interactions in Spanish

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────┐
│                  AgentOrchestrator                      │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────┐ │
│  │ ListAgent  │  │ TaskAgent  │  │ NoteAgent        │ │
│  └──────┬─────┘  └──────┬─────┘  └────────┬─────────┘ │
│         │                │                 │            │
│         └────────────────┴─────────────────┘            │
│                          │                              │
│                 ┌────────▼─────────┐                    │
│                 │ EnrichmentAgent  │◄───────────────┐  │
│                 └────────┬─────────┘                 │  │
│                          │                           │  │
│         ┌────────────────┴─────────────┐             │  │
│         │                              │             │  │
│  ┌──────▼──────┐              ┌────────▼────────┐   │  │
│  │ Field       │              │ Conversation    │   │  │
│  │ Detector    │              │ State Manager   │   │  │
│  └─────────────┘              └─────────────────┘   │  │
│                                                      │  │
│  ┌──────────────────────────────────────────────┐   │  │
│  │         EnrichmentPrompts (Spanish)          │   │  │
│  └──────────────────────────────────────────────┘   │  │
│                                                      │  │
└──────────────────────────────────────────────────────┘  │
                                                          │
                        User Response ────────────────────┘
```

### Flow Diagram

```
User: "Agregar leche a la lista"
  │
  ▼
┌─────────────────────────────────┐
│  IntentClassifier → LIST        │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  ListAgent.handle()             │
│  - Extracts: "leche"            │
│  - Missing: location, tags      │
│  - Returns: needs_enrichment    │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  EnrichmentAgent.analyze()      │
│  - Detects missing: location    │
│  - Priority: HIGH (shopping)    │
│  - Decision: ASK                │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  EnrichmentAgent.generate_q()   │
│  → "¿En qué tienda?"            │
└─────────────┬───────────────────┘
              │
              ▼
User: "Mercadona"
  │
  ▼
┌─────────────────────────────────┐
│  EnrichmentAgent.process_ans()  │
│  - Extracts: location="Mercado" │
│  - Still missing: tags          │
│  - Decision: SKIP (low value)   │
└─────────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  EnrichmentAgent.complete()     │
│  - Calls: ListTool.add_item()   │
│  - With enriched data           │
└─────────────────────────────────┘
```

## Data Structures

### EnrichmentContext

```python
@dataclass
class EnrichmentContext:
    """Tracks state of an enrichment conversation."""
    
    # Original request
    chat_id: str
    user_id: str
    agent_type: str  # "list", "task", "note"
    operation: str   # "add_item", "create_task", etc.
    original_data: dict[str, Any]
    
    # Enrichment state
    missing_fields: list[str]  # ["location", "tags", "people"]
    asked_fields: list[str]     # Already asked about
    gathered_data: dict[str, Any]  # Answers collected
    
    # Conversation tracking
    turn_count: int = 0
    max_turns: int = 3  # Don't be annoying
    priority: str = "medium"  # "high", "medium", "low", "skip"
    
    # Metadata
    created_at: str
    last_updated: str
    
    def is_complete(self) -> bool:
        """Check if enrichment is done."""
        return (
            not self.missing_fields or 
            self.turn_count >= self.max_turns or
            self.priority == "skip"
        )
    
    def next_field_to_ask(self) -> str | None:
        """Get next most valuable field to ask about."""
        # Priority order based on agent type
        for field in self.missing_fields:
            if field not in self.asked_fields:
                return field
        return None
```

### EnrichmentRule

```python
@dataclass
class EnrichmentRule:
    """Rule for when/how to ask about a field."""
    
    field_name: str
    agent_types: list[str]  # Which agents this applies to
    priority: Callable[[dict], str]  # Function to determine priority
    question_template: str  # Spanish question
    follow_up: str | None  # Optional clarification
    examples: list[str]  # Example answers
    
    def should_ask(self, agent_type: str, data: dict) -> bool:
        """Determine if we should ask about this field."""
        if agent_type not in self.agent_types:
            return False
        
        if self.field_name in data and data[self.field_name]:
            return False  # Already have it
        
        priority = self.priority(data)
        return priority in ["high", "medium"]
```

## Enrichment Rules

### People Field

```python
PEOPLE_RULE = EnrichmentRule(
    field_name="people",
    agent_types=["list", "task", "note"],
    priority=lambda data: "high" if any(
        word in data.get("text", "").lower() 
        for word in ["para", "con", "llamar", "reunión", "hablar"]
    ) else "low",
    question_template="¿Con quién está relacionado esto? (o escribe 'nadie' para omitir)",
    follow_up="Puedes mencionar varios nombres: 'Juan y María'",
    examples=["Juan", "María", "Juan y Pedro", "el equipo"]
)
```

### Location Field

```python
LOCATION_RULE = EnrichmentRule(
    field_name="location",
    agent_types=["list", "task", "note"],
    priority=lambda data: "high" if any(
        word in data.get("text", "").lower()
        for word in ["comprar", "ir", "reunión", "visitar", "en"]
    ) else "medium",
    question_template="¿En qué lugar? (o comparte una ubicación 📍)",
    follow_up="Ejemplo: 'Mercadona Gran Vía' o envía tu ubicación",
    examples=["Mercadona", "Oficina central", "Casa de Juan"]
)
```

### Tags Field

```python
TAGS_RULE = EnrichmentRule(
    field_name="tags",
    agent_types=["list", "task", "note"],
    priority=lambda data: "low",  # Optional, nice to have
    question_template="¿Quieres añadir etiquetas? (ej: urgente, trabajo) o 'no'",
    follow_up=None,
    examples=["urgente", "trabajo", "personal", "salud"]
)
```

### Due Date (Tasks only)

```python
DUE_DATE_RULE = EnrichmentRule(
    field_name="due_at",
    agent_types=["task"],
    priority=lambda data: "high",  # Tasks should have deadlines
    question_template="¿Para cuándo es esta tarea?",
    follow_up="Ejemplo: 'mañana', 'viernes', 'en 3 días', '25/10/2025'",
    examples=["mañana", "el viernes", "en 2 días", "25/10/2025"]
)
```

## LLM Prompts

### Field Detector Prompt

```python
FIELD_DETECTOR_PROMPT = """
Analiza el siguiente texto y extrae información sobre personas, lugares y contexto.

TEXTO: "{text}"

Extrae:
1. PERSONAS: Nombres de personas mencionadas (o lista vacía si no hay)
2. LUGAR: Ubicación mencionada (o null si no se menciona)
3. ETIQUETAS: Categorías implícitas (urgente, trabajo, personal, etc.)
4. CONTEXTO: Información adicional relevante

Responde en JSON:
{{
  "people": ["nombre1", "nombre2"],
  "location": "nombre del lugar o null",
  "tags": ["tag1", "tag2"],
  "notes": "contexto adicional o null"
}}

Ejemplos:
- "Comprar leche en Mercadona para Juan" → {{"people": ["Juan"], "location": "Mercadona", "tags": ["compras"]}}
- "Llamar a María sobre el proyecto" → {{"people": ["María"], "tags": ["trabajo", "llamada"]}}
- "Reunión mañana en la oficina" → {{"location": "la oficina", "tags": ["reunión"]}}
"""
```

### Response Extractor Prompt

```python
RESPONSE_EXTRACTOR_PROMPT = """
El usuario respondió a una pregunta sobre: {field_name}

PREGUNTA: {question}
RESPUESTA: {answer}

Extrae la información en el formato correcto:

- Si el campo es "people": extrae lista de nombres
- Si el campo es "location": extrae nombre del lugar
- Si el campo es "tags": extrae lista de etiquetas
- Si dice "no", "nadie", "ninguno", "omitir": devuelve null

Responde SOLO con el valor extraído (JSON array para listas, string para texto, null si no aplica).

Ejemplos:
Pregunta sobre people, respuesta "Juan y María" → ["Juan", "María"]
Pregunta sobre location, respuesta "Mercadona de Gran Vía" → "Mercadona Gran Vía"
Pregunta sobre tags, respuesta "no" → null
"""
```

## State Management

### Conversation State Store

```python
class ConversationStateManager:
    """Manages active enrichment conversations."""
    
    def __init__(self):
        self._active_contexts: dict[str, EnrichmentContext] = {}
        self._lock = asyncio.Lock()
    
    async def create_context(
        self, 
        chat_id: str, 
        agent_type: str,
        operation: str,
        data: dict
    ) -> EnrichmentContext:
        """Start new enrichment session."""
        async with self._lock:
            context = EnrichmentContext(
                chat_id=chat_id,
                user_id=data.get("user_id"),
                agent_type=agent_type,
                operation=operation,
                original_data=data,
                missing_fields=[],
                asked_fields=[],
                gathered_data={},
                created_at=datetime.now(UTC).isoformat()
            )
            self._active_contexts[chat_id] = context
            return context
    
    async def get_context(self, chat_id: str) -> EnrichmentContext | None:
        """Get active enrichment context for chat."""
        return self._active_contexts.get(chat_id)
    
    async def update_context(self, chat_id: str, context: EnrichmentContext):
        """Update existing context."""
        async with self._lock:
            context.last_updated = datetime.now(UTC).isoformat()
            self._active_contexts[chat_id] = context
    
    async def complete_context(self, chat_id: str) -> EnrichmentContext:
        """Mark enrichment as complete and remove from active."""
        async with self._lock:
            return self._active_contexts.pop(chat_id, None)
```

## Integration Points

### 1. Agent Response Enhancement

Agents return enriched response objects:

```python
@dataclass
class AgentResponse:
    message: str  # User-facing message
    success: bool
    needs_enrichment: bool  # NEW
    extracted_data: dict[str, Any]  # Data extracted from user input
    operation: str  # What operation to perform
```

### 2. Orchestrator Integration

```python
class AgentOrchestrator:
    def __init__(self, ...):
        # ... existing ...
        self.enrichment_agent = EnrichmentAgent(llm_service)
        self.state_manager = ConversationStateManager()
    
    async def handle_message(self, message, chat_id, user_id):
        # Check if we're in an enrichment conversation
        context = await self.state_manager.get_context(chat_id)
        
        if context:
            # Process as enrichment response
            return await self._handle_enrichment_response(
                message, context
            )
        
        # Normal flow: classify and route
        intent = await self.intent_classifier.classify(message)
        agent = self.agents[intent]
        response = await agent.handle(message, chat_id, user_id)
        
        # Check if enrichment needed
        if response.needs_enrichment:
            return await self._start_enrichment(
                chat_id, user_id, agent.name, response
            )
        
        return response
```

## Success Criteria

- ✅ EnrichmentAgent can detect missing fields
- ✅ Generates natural Spanish questions
- ✅ Tracks multi-turn conversations
- ✅ Extracts answers and maps to fields
- ✅ Knows when to stop asking (max turns, low priority)
- ✅ Completes operation with enriched data
- ✅ Handles "skip" / "no" responses gracefully
- ✅ Integrates seamlessly with existing agents

## Testing Strategy

1. **Unit Tests**:
   - Field detection from text
   - Question generation
   - Answer extraction
   - State management

2. **Integration Tests**:
   - Full enrichment flow
   - Multi-turn conversations
   - Integration with ListAgent/TaskAgent

3. **Conversation Tests**:
   - Natural flow scenarios
   - Edge cases (skip, unclear answers)
   - Maximum turn limits

## Next Steps

1. Implement `EnrichmentAgent` class ✅ Next
2. Implement `FieldDetector` logic
3. Implement `ConversationStateManager`
4. Create enrichment prompts
5. Update `AgentOrchestrator`
6. Build test suite
7. Test with real conversations

---

**Estimated Time**: 3-4 hours  
**Complexity**: Medium-High  
**Dependencies**: Phase 1 (complete ✅)
