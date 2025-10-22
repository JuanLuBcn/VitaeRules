"""
Example integration of new agent-based architecture.

This shows the simplified flow:
1. Classify intent
2. Route to specialized agent
3. Handle confirmation if needed
4. Execute and return result
"""

from app.agents import (
    IntentClassifier,
    IntentType,
    ListAgent,
    NoteAgent,
    QueryAgent,
    TaskAgent,
)
from app.llm import LLMService
from app.memory import MemoryService


class AgentOrchestrator:
    """
    Simplified orchestrator that routes messages to specialized agents.
    
    Replaces the complex Router → Planner → Enricher → Clarifier flow.
    """
    
    def __init__(self, llm_service: LLMService, memory_service: MemoryService):
        """Initialize orchestrator with all agents."""
        self.classifier = IntentClassifier(llm_service)
        
        # Initialize specialized agents
        self.agents = {
            IntentType.LIST: ListAgent(llm_service, memory_service),
            IntentType.TASK: TaskAgent(llm_service, memory_service),
            IntentType.NOTE: NoteAgent(llm_service, memory_service),
            IntentType.QUERY: QueryAgent(llm_service, memory_service),
        }
        
        # Track pending confirmations per chat
        self.pending_confirmations = {}
    
    async def handle_message(
        self, message: str, chat_id: str, user_id: str
    ) -> dict:
        """
        Handle incoming message.
        
        Returns:
            dict with:
                - message: Response to show user
                - needs_confirmation: bool
                - data: Optional data for confirmation
        """
        # Check for pending confirmation
        if chat_id in self.pending_confirmations:
            return await self._handle_confirmation(message, chat_id, user_id)
        
        # Step 1: Classify intent
        intent, confidence = await self.classifier.classify(message)
        
        # Step 2: Low confidence? Ask for clarification
        if confidence < 0.7:
            return {
                "message": self._build_clarification_message(intent, confidence),
                "needs_confirmation": False,
            }
        
        # Step 3: Unknown intent?
        if intent == IntentType.UNKNOWN:
            return {
                "message": "No estoy seguro de qué quieres que haga. Prueba: 'Recuerda que...', 'Añade a la lista...', 'Recuérdame...', o haz una pregunta.",
                "needs_confirmation": False,
            }
        
        # Step 4: Route to specialized agent
        agent = self.agents.get(intent)
        if not agent:
            return {
                "message": f"El agente para {intent} aún no está implementado.",
                "needs_confirmation": False,
            }
        
        result = await agent.handle(message, chat_id, user_id)
        
        # Step 5: Need confirmation?
        if result.needs_confirmation:
            self.pending_confirmations[chat_id] = {
                "agent": agent,
                "data": result.data,
            }
            return {
                "message": result.preview or result.message,
                "needs_confirmation": True,
            }
        
        # Step 6: Return result
        return {
            "message": result.message,
            "needs_confirmation": False,
            "success": result.success,
            "error": result.error,
        }
    
    async def _handle_confirmation(
        self, message: str, chat_id: str, user_id: str
    ) -> dict:
        """Handle confirmation response (yes/no)."""
        message_lower = message.lower()
        
        # Get pending action
        pending = self.pending_confirmations.get(chat_id)
        if not pending:
            return {
                "message": "No hay ninguna acción pendiente de confirmar.",
                "needs_confirmation": False,
            }
        
        # Check if user confirmed
        confirmed = any(
            word in message_lower for word in ["yes", "sí", "si", "ok", "claro", "confirma", "vale"]
        )
        
        if not confirmed:
            # User cancelled
            del self.pending_confirmations[chat_id]
            return {
                "message": "Acción cancelada.",
                "needs_confirmation": False,
            }
        
        # Execute confirmed action
        agent = pending["agent"]
        data = pending["data"]
        
        result = await agent.execute_confirmed(data)
        
        # Clear pending
        del self.pending_confirmations[chat_id]
        
        return {
            "message": result.message,
            "needs_confirmation": False,
            "success": result.success,
            "error": result.error,
        }
    
    def _build_clarification_message(self, intent: IntentType, confidence: float) -> str:
        """Build clarification message when confidence is low."""
        return f"""No estoy muy seguro de qué quieres que haga (confianza: {confidence:.0%}).

¿Querías:
• 📝 Guardar una nota o memoria?
• ✅ Crear o gestionar una tarea?
• 📋 Añadir algo a una lista?
• ❓ Hacer una pregunta sobre tus datos?

Por favor, intenta de nuevo con más detalle."""


# Example usage
async def example():
    """Example of using the new agent system."""
    llm = LLMService()
    memory = MemoryService()
    orchestrator = AgentOrchestrator(llm, memory)
    
    # Example 1: Add to list
    result = await orchestrator.handle_message(
        message="Añade mantequilla a la lista de la compra",
        chat_id="123",
        user_id="user1",
    )
    print(f"Response: {result['message']}")
    print(f"Needs confirmation: {result['needs_confirmation']}")
    
    # Confirm
    if result["needs_confirmation"]:
        confirm_result = await orchestrator.handle_message(
            message="yes",
            chat_id="123",
            user_id="user1",
        )
        print(f"After confirmation: {confirm_result['message']}")
    
    # Example 2: Create task
    result = await orchestrator.handle_message(
        message="Remind me to call John tomorrow",
        chat_id="123",
        user_id="user1",
    )
    print(f"Response: {result['message']}")
    
    # Example 3: Save note
    result = await orchestrator.handle_message(
        message="Remember that John likes coffee",
        chat_id="123",
        user_id="user1",
    )
    print(f"Response: {result['message']}")
    
    # Example 4: Query
    result = await orchestrator.handle_message(
        message="What did I save about John?",
        chat_id="123",
        user_id="user1",
    )
    print(f"Response: {result['message']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example())
