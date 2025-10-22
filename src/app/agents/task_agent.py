"""Task management agent."""

from datetime import datetime
from typing import Any

from app.llm import LLMService
from app.tools.task_tool import TaskTool
from app.tracing import get_tracer

from .base import AgentResult, BaseAgent

logger = get_tracer()


class TaskAgent(BaseAgent):
    """
    Handles all task operations.
    
    Understands:
    - Create tasks: "Remind me to call John tomorrow"
    - Complete tasks: "Mark laundry as done"
    - Update tasks: "Change meeting to 3pm"
    - Query tasks: "What's on my task list?"
    """
    
    def __init__(self, llm_service: LLMService, memory_service=None):
        """Initialize task agent."""
        super().__init__(llm_service, memory_service)
        self.task_tool = TaskTool()
    
    @property
    def name(self) -> str:
        """Agent name."""
        return "TaskAgent"
    
    @property
    def description(self) -> str:
        """Agent description."""
        return "Manages tasks and reminders - create, complete, update"
    
    async def can_handle(self, message: str) -> tuple[bool, float]:
        """Check if message is about tasks."""
        message_lower = message.lower()
        
        # Strong task indicators
        task_words = ["remind me", "task", "tarea", "need to", "tengo que", "debo"]
        if any(word in message_lower for word in task_words):
            return True, 0.9
        
        return False, 0.0
    
    async def handle(
        self,
        message: str,
        chat_id: str,
        user_id: str,
        context: dict[str, Any] | None = None
    ) -> AgentResult:
        """Handle task operation."""
        logger.info(f"TaskAgent handling: {message[:100]}")
        
        # Determine operation type
        operation = self._detect_operation(message)
        
        if operation == "query":
            return await self._handle_query(message, chat_id, user_id)
        elif operation == "create":
            return await self._handle_create(message, chat_id, user_id)
        elif operation == "complete":
            return await self._handle_complete(message, chat_id, user_id)
        else:
            return AgentResult(
                success=False,
                message="No estoy seguro de qué quieres hacer con las tareas. Prueba: 'Recuérdame...' o '¿Cuáles son mis tareas?'",
                error="Unknown task operation"
            )
    
    def _detect_operation(self, message: str) -> str:
        """Detect task operation type."""
        message_lower = message.lower()
        
        # Query patterns
        if any(word in message_lower for word in ["what", "qué", "cuáles", "show", "muestra", "list"]):
            return "query"
        
        # Complete patterns
        if any(word in message_lower for word in ["done", "complete", "finish", "hecho", "terminado", "completado"]):
            return "complete"
        
        # Create is default
        return "create"
    
    async def _handle_query(
        self, message: str, chat_id: str, user_id: str
    ) -> AgentResult:
        """Handle task query."""
        try:
            result = await self.task_tool.execute({
                "operation": "list_tasks",
                "user_id": user_id,
                "chat_id": chat_id,
            })
            
            tasks = result.get("tasks", [])
            
            if not tasks:
                response = "📋 No tienes ninguna tarea."
            else:
                # Separate pending and completed
                pending = [t for t in tasks if not t.get("completed")]
                completed = [t for t in tasks if t.get("completed")]
                
                response = "📋 **Tus Tareas**\n\n"
                
                if pending:
                    response += "**Pendientes:**\n"
                    for task in pending[:5]:  # Show max 5
                        title = task.get("title", "Sin título")
                        due = task.get("due_at", "Sin fecha")
                        response += f"⬜ {title}\n"
                        if due != "Sin fecha":
                            response += f"   📅 Fecha: {due}\n"
                    
                    if len(pending) > 5:
                        response += f"\n_...y {len(pending) - 5} más_\n"
                
                if completed:
                    response += f"\n**Completadas:** {len(completed)} tarea(s) ✅"
            
            return AgentResult(success=True, message=response)
            
        except Exception as e:
            logger.error(f"Task query failed: {e}")
            return AgentResult(
                success=False,
                message="Lo siento, no pude recuperar tus tareas.",
                error=str(e)
            )
    
    async def _handle_create(
        self, message: str, chat_id: str, user_id: str
    ) -> AgentResult:
        """Handle creating a task."""
        # Extract task details using LLM
        task_data = self._extract_task_details(message)
        
        if not task_data.get("title"):
            return AgentResult(
                success=False,
                message="No pude entender la tarea. Prueba: 'Recuérdame llamar a Juan mañana'",
                error="No task title found"
            )
        
        # Create preview
        title = task_data["title"]
        due_date = task_data.get("due_at", "No especificada")
        priority = task_data.get("priority", "media")
        
        preview = (
            f"📋 **¿Crear esta tarea?**\n\n"
            f"**Tarea:** {title}\n"
            f"**Fecha:** {due_date}\n"
            f"**Prioridad:** {priority}"
        )
        
        # Return with confirmation needed
        return AgentResult(
            success=True,
            message=preview,
            needs_confirmation=True,
            preview=preview,
            data={
                "operation": "create",
                "task_data": task_data,
                "chat_id": chat_id,
                "user_id": user_id,
            }
        )
    
    async def execute_confirmed(self, data: dict[str, Any]) -> AgentResult:
        """Execute confirmed task operation."""
        operation = data.get("operation")
        
        if operation == "create":
            return await self._execute_create(data)
        else:
            return AgentResult(
                success=False,
                message="Unknown operation",
                error=f"Unsupported operation: {operation}"
            )
    
    async def _execute_create(self, data: dict[str, Any]) -> AgentResult:
        """Execute task creation."""
        task_data = data["task_data"]
        chat_id = data["chat_id"]
        user_id = data["user_id"]
        
        try:
            result = await self.task_tool.execute({
                "operation": "create_task",
                "title": task_data["title"],
                "due_at": task_data.get("due_at"),
                "priority": task_data.get("priority", 2),  # medium = 2
                "user_id": user_id,
                "chat_id": chat_id,
            })
            
            title = task_data["title"]
            response = f"✅ Tarea creada: **{title}**"
            
            return AgentResult(success=True, message=response)
            
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return AgentResult(
                success=False,
                message=f"No pude crear la tarea. {str(e)}",
                error=str(e)
            )
    
    async def _handle_complete(
        self, message: str, chat_id: str, user_id: str
    ) -> AgentResult:
        """Handle completing a task."""
        # TODO: Implement task completion
        return AgentResult(
            success=False,
            message="Completar tareas aún no está implementado. ¡Próximamente!",
            error="Not implemented"
        )
    
    def _extract_task_details(self, message: str) -> dict[str, Any]:
        """Extract task details from message using LLM."""
        prompt = f"""Extract task details from this message:

Mensaje: "{message}"

Devuelve JSON:
{{
    "title": "descripción de la tarea",
    "due_at": "fecha ISO o null",
    "priority": "alta|media|baja"
}}

Ejemplos:
- "Recuérdame llamar a Juan mañana" → {{"title": "Llamar a Juan", "due_at": "mañana", "priority": "media"}}
- "Tengo que terminar el informe para el viernes" → {{"title": "Terminar el informe", "due_at": "viernes", "priority": "alta"}}
- "Comprar comida" → {{"title": "Comprar comida", "due_at": null, "priority": "media"}}"""
        
        try:
            result = self.llm.generate_json(
                prompt=prompt,
                system_prompt="Eres un extractor de detalles de tareas. Devuelve SOLO JSON válido."
            )
            
            return {
                "title": result.get("title", ""),
                "due_at": result.get("due_at"),
                "priority": result.get("priority", "media"),
            }
            
        except Exception as e:
            logger.error(f"Task extraction failed: {e}")
            # Fallback: use full message as title
            return {
                "title": message,
                "due_at": None,
                "priority": "media",
            }
