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
            reasoning = result.get("reasoning", "")
            
            # Map to enum
            try:
                intent = IntentType(intent_str)
            except ValueError:
                intent = IntentType.UNKNOWN
                confidence = 0.0
            
            logger.info(
                "Intent classified",
                extra={
                    "intent": intent.value, 
                    "confidence": confidence,
                    "reasoning": reasoning,
                    "message": message[:100]
                }
            )
            
            return intent, confidence
            
        except Exception as e:
            logger.error("Classification error", extra={"error": str(e)})
            return IntentType.UNKNOWN, 0.0
    
    def _build_classification_prompt(self, message: str) -> str:
        """Build classification prompt."""
        return f"""Analiza la INTENCIÓN SEMÁNTICA de este mensaje y clasifícalo en UNA categoría.

Mensaje del usuario: "{message}"

## Categorías (piensa en el PROPÓSITO, no en palabras específicas):

### 1. **task** - Acciones FUTURAS que el usuario debe hacer
**Pregunta clave:** ¿Es algo que el usuario necesita HACER más adelante?
- Crear recordatorios para acciones futuras
- Consultar tareas pendientes
- Marcar tareas como completadas
- Cualquier acción con temporalidad futura

Ejemplos:
- "Recuérdame llamar a Juan" → acción futura
- "Tengo que comprar leche" → acción pendiente
- "Debo terminar el informe" → obligación futura
- "Avísame mañana" → recordatorio temporal
- "¿Qué tareas tengo?" → consulta de pendientes

### 2. **note** - Guardar INFORMACIÓN o hechos (sin acción futura)
**Pregunta clave:** ¿Es información para recordar, sin necesidad de hacer algo?
- Guardar datos, preferencias, hechos
- Memorias de eventos pasados
- Información sobre personas o cosas
- NO implica acción futura del usuario

Ejemplos:
- "Recuerda que a Juan le gusta el café" → preferencia, no acción
- "Hemos ido a la playa" → memoria de evento
- "El cumpleaños de Sara es en junio" → dato
- "La contraseña es abc123" → información
- "A María le gustan las flores" → preferencia

### 3. **list** - Gestionar COLECCIONES de elementos
**Pregunta clave:** ¿Está agregando/quitando/consultando elementos de una lista?
- Añadir o quitar elementos de listas
- Ver contenido de listas específicas
- Limpiar o gestionar listas

Ejemplos:
- "Añade leche a la compra" → agregar a lista
- "Pon mantequilla en la lista" → agregar a lista
- "Quita huevos" → remover de lista
- "¿Qué hay en mi lista de compras?" → consulta de lista
- "Borra toda la lista" → gestión de lista

### 4. **query** - Buscar o recuperar INFORMACIÓN guardada
**Pregunta clave:** ¿Está preguntando por información que guardó antes?
- Búsquedas de información pasada
- Preguntas sobre eventos, personas, o datos guardados
- Recuperación de contexto histórico

Ejemplos:
- "¿Qué hice ayer?" → buscar eventos pasados
- "¿Qué sé de Juan?" → recuperar información
- "Cuéntame sobre mi reunión" → buscar contexto
- "¿Cuándo fue mi cita?" → buscar dato temporal

### 5. **unknown** - No está claro o es ambiguo

## Proceso de clasificación:

1. **Ignora palabras específicas** - No te bases solo en "recuerda", "añade", etc.
2. **Analiza el PROPÓSITO semántico**:
   - ¿Qué QUIERE el usuario?
   - ¿Es una acción futura? → task
   - ¿Es guardar información? → note
   - ¿Es gestionar una lista? → list
   - ¿Es buscar algo guardado? → query

3. **Considera el CONTEXTO temporal**:
   - Futuro/pendiente → probablemente task
   - Pasado/presente sin acción → probablemente note o query
   - Lista de elementos → probablemente list

4. **Sé decisivo pero honesto**:
   - Alta confianza (0.8-1.0): Intención clara
   - Confianza media (0.5-0.8): Probable pero con ambigüedad
   - Baja confianza (0.0-0.5): Usa "unknown"

Devuelve JSON:
{{
    "intent": "note|task|list|query|unknown",
    "confidence": 0.0-1.0,
    "reasoning": "explicación del razonamiento semántico"
}}"""
    
    def _get_system_prompt(self) -> str:
        """System prompt for classifier."""
        return """Eres un clasificador de intenciones SEMÁNTICO. Analiza el PROPÓSITO del mensaje, no solo palabras clave.

PIENSA como un humano entendería la intención:
- ¿Qué QUIERE hacer el usuario?
- ¿Cuál es el OBJETIVO del mensaje?
- ¿Hay una ACCIÓN FUTURA implícita o explícita?

NO te bases en palabras específicas como "recuerda", "añade", etc.
En su lugar, analiza el SIGNIFICADO completo del mensaje.

Devuelve SOLO JSON válido, sin markdown, sin explicaciones.

Confianza basada en claridad de intención:
- Alta (0.8-1.0): El propósito es obvio sin ambigüedad
- Media (0.5-0.8): Probable pero podría interpretarse de otra forma
- Baja (0.0-0.5): Ambiguo, usa "unknown"

Ejemplo de razonamiento correcto:
- "Recuérdame llamar a Juan" → TASK (acción futura: llamar)
- "Recuerda que a Juan le gusta café" → NOTE (información, sin acción)
- "Hemos ido a la playa" → NOTE (memoria pasada, sin acción futura)
- "Tengo que comprar leche" → TASK (obligación/acción pendiente)
- "Pon leche en la lista" → LIST (gestión de colección)"""
