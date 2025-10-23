"""Simple intent classifier for routing messages to specialized agents."""

from enum import Enum

from app.llm import LLMService
from app.tracing import get_tracer

logger = get_tracer()


class IntentType(str, Enum):
    """Core intent types - keep it simple!"""
    
    NOTE = "note"      # Save information, memories, facts
    TASK = "task"      # Create, manage tasks
    LIST = "list"      # Manage lists (shopping, etc.)
    QUERY = "query"    # Search and retrieve information
    UNKNOWN = "unknown"  # Can't determine


class IntentClassifier:
    """
    Simple intent classifier using LLM.
    
    Job: Determine if message is about notes, tasks, lists, or queries.
    That's it! Specialized agents handle the details.
    """
    
    def __init__(self, llm_service: LLMService):
        """Initialize classifier with LLM service."""
        self.llm = llm_service
    
    async def classify(self, message: str) -> tuple[IntentType, float]:
        """
        Classify message intent.
        
        Args:
            message: User message
            
        Returns:
            (intent, confidence) where confidence is 0.0-1.0
        """
        logger.debug("Classifying intent", extra={"message": message[:100]})
        
        prompt = self._build_classification_prompt(message)
        
        try:
            result = self.llm.generate_json(
                prompt=prompt,
                system_prompt=self._get_system_prompt()
            )
            
            intent_str = result.get("intent", "unknown")
            confidence = result.get("confidence", 0.0)
            
            # Map to enum
            try:
                intent = IntentType(intent_str)
            except ValueError:
                intent = IntentType.UNKNOWN
                confidence = 0.0
            
            logger.info(
                "Intent classified",
                extra={"intent": intent.value, "confidence": confidence}
            )
            
            return intent, confidence
            
        except Exception as e:
            logger.error("Classification error", extra={"error": str(e)})
            return IntentType.UNKNOWN, 0.0
    
    def _build_classification_prompt(self, message: str) -> str:
        """Build classification prompt."""
        return f"""Clasifica este mensaje del usuario en UNA categoría de intención.

Mensaje del usuario: "{message}"

Categorías de intención:

1. **note** - Guardar información, memorias, hechos
   Ejemplos:
   - "Recuerda que a Juan le gusta el café"
   - "El cumpleaños de Sara es el 15 de junio"
   - "La contraseña es abc123"
   - "Nota: la reunión fue bien"

2. **task** - Crear o gestionar tareas/recordatorios, ver tareas
   Ejemplos:
   - "Recuérdame llamar a Juan mañana"
   - "Tengo que terminar el informe para el viernes"
   - "Crea una tarea para comprar comida"
   - "Marca la lavandería como hecha"
   - "¿Cuáles son mis tareas?"
   - "Muéstrame mis tareas pendientes"

3. **list** - Gestionar listas (añadir, eliminar, ver elementos)
   Ejemplos:
   - "Añade leche a la lista de la compra"
   - "Añade mantequilla a la lista de la compra"
   - "Quita huevos de la lista"
   - "¿Qué hay en mi lista de la compra?"
   - "Muéstrame la lista"
   - "¿Qué hay en la lista?"

4. **query** - Buscar información general guardada, preguntas sobre el pasado
   Ejemplos:
   - "¿Qué hice ayer?"
   - "¿Cuándo es mi cita con el dentista?"
   - "Cuéntame sobre mi reunión con Sara"
   - "¿Qué guardé sobre María?"
   - "¿Qué sé de Juan?"

5. **unknown** - No se puede determinar o no está claro

REGLAS CRÍTICAS:
- "¿Qué hay en la lista?" o "¿Qué hay en mi lista de X?" → "list"
- "¿Cuáles son mis tareas?" o "Muestra tareas" → "task"
- "¿Qué guardé sobre X?" o "¿Qué sé de X?" → "query"
- Si el mensaje contiene "recuerda", "nota", "guarda" → "note"
- Si el mensaje dice "recuérdame", "tarea", "tengo que" → "task"
- Si el mensaje dice "añade", "agrega" con "lista" → "list"
- Devuelve confianza 0.0-1.0 (1.0 = muy seguro)
- Si es ambiguo, devuelve "unknown" con baja confianza

Devuelve JSON:
{{
    "intent": "note|task|list|query|unknown",
    "confidence": 0.0-1.0,
    "reasoning": "explicación breve"
}}"""
    
    def _get_system_prompt(self) -> str:
        """System prompt for classifier."""
        return """Eres un clasificador de intenciones. Tu ÚNICO trabajo es categorizar mensajes de usuarios.

Devuelve SOLO JSON válido, sin markdown, sin explicaciones.

Sé decisivo pero honesto sobre la confianza:
- Alta confianza (0.8-1.0): Intención clara, categoría obvia
- Confianza media (0.5-0.8): Categoría probable pero con algo de ambigüedad
- Baja confianza (0.0-0.5): No está claro, usa "unknown"

En caso de duda, usa "unknown" - se le pedirá al usuario que aclare."""
