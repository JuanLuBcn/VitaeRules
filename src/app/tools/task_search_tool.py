"""Task Search Tool for CrewAI agents."""

from typing import Optional, Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool as CrewAIBaseTool

from app.tools.task_tool import TaskTool
from app.tracing import get_tracer


class TaskSearchToolSchema(BaseModel):
    """Input schema for TaskSearchTool."""

    completed: Optional[bool] = Field(
        default=None,
        description="Filter by completion status: True=completed, False=pending, None=all tasks"
    )
    search_query: Optional[str] = Field(
        default=None,
        description="Optional text to search in task titles and descriptions"
    )


class TaskSearchTool(CrewAIBaseTool):
    """Tool for searching and listing tasks."""

    name: str = "task_search"
    description: str = (
        "Search and list tasks with optional filtering by completion status. "
        "Use this tool to find pending tasks, completed tasks, or search by text. "
        "User context is automatically included."
    )
    args_schema: Type[BaseModel] = TaskSearchToolSchema
    
    # Use class attributes to avoid Pydantic validation
    _task_tool: TaskTool | None = None
    _user_id: str = "default"
    _chat_id: str = "default"

    def __init__(
        self, 
        task_tool: TaskTool | None = None,
        user_id: str = "default",
        chat_id: str = "default"
    ):
        """Initialize Task Search Tool.

        Args:
            task_tool: Task tool instance (default: create new)
            user_id: User identifier to store in context
            chat_id: Chat identifier to store in context
        """
        super().__init__()
        # Store in class attributes to avoid Pydantic validation
        TaskSearchTool._task_tool = task_tool or TaskTool()
        TaskSearchTool._user_id = user_id
        TaskSearchTool._chat_id = chat_id
        tracer = get_tracer()
        tracer.debug(f"TaskSearchTool initialized with user_id={user_id}, chat_id={chat_id}")

    def _run(
        self,
        completed: Optional[bool] = None,
        search_query: Optional[str] = None,
    ) -> str:
        """Search tasks synchronously.

        Args:
            completed: Filter by completion status (None = all tasks)
            search_query: Optional text to search in title/description

        Returns:
            Formatted list of tasks
        
        Note: user_id and chat_id are taken from the tool's stored context
        """
        tracer = get_tracer()
        
        # Handle case where LLM outputs array instead of dict
        if isinstance(completed, list):
            tracer.warning(f"Received array for 'completed': {completed}, extracting first element")
            completed = completed[0] if len(completed) > 0 and isinstance(completed[0], (bool, type(None))) else None
        
        if isinstance(search_query, list):
            tracer.warning(f"Received array for 'search_query': {search_query}, extracting first element")
            search_query = search_query[0] if len(search_query) > 0 and isinstance(search_query[0], str) else None
        
        try:
            # Build arguments for list_tasks using stored context
            args = {
                "operation": "list_tasks",
                "user_id": self._user_id,
                "chat_id": self._chat_id,
            }

            if completed is not None:
                args["completed"] = completed

            # Execute list_tasks (it's async, but we're in a sync tool method)
            # CrewAI calls _run() synchronously, but our TaskTool.execute() is async
            import asyncio
            
            # Check if there's already an event loop running
            try:
                loop = asyncio.get_running_loop()
                # We're in an event loop - this happens when Telegram bot calls CrewAI
                # We can't use run_until_complete or asyncio.run, so we need to await
                # But we're in a sync function... so we need to create a new thread
                tracer.warning("Event loop already running - using thread executor")
                from concurrent.futures import ThreadPoolExecutor
                import threading
                
                def run_async_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(TaskSearchTool._task_tool.execute(args))
                    finally:
                        new_loop.close()
                
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(run_async_in_thread)
                    result = future.result(timeout=30)
                    
            except RuntimeError:
                # No event loop running - safe to use asyncio.run()
                result = asyncio.run(TaskSearchTool._task_tool.execute(args))

            # Extract tasks from result
            if "error" in result:
                return f"Task search error: {result['error']}"

            tasks = result.get("tasks", [])

            # Filter by search query if provided
            if search_query and tasks:
                search_lower = search_query.lower()
                tasks = [
                    t for t in tasks
                    if search_lower in t.get("title", "").lower()
                    or search_lower in t.get("description", "").lower()
                ]

            # Format results
            if not tasks:
                return "No tasks found matching the criteria."

            formatted = []
            for i, task in enumerate(tasks, 1):
                status = "✓ Completed" if task.get("completed") else "○ Pending"
                priority_map = {0: "Low", 1: "Medium", 2: "High", 3: "Urgent"}
                priority = priority_map.get(task.get("priority", 0), "Unknown")

                formatted.append(
                    f"\n{i}. [{status}] **{task['title']}** (Priority: {priority})\n"
                    f"   Description: {task.get('description', 'No description')}\n"
                    f"   Due: {task.get('due_at', 'No due date')}\n"
                    f"   Created: {task.get('created_at', 'Unknown')}"
                )

                # Add optional fields if present
                if task.get("people"):
                    formatted.append(f"   People: {', '.join(task['people'])}")
                if task.get("tags"):
                    formatted.append(f"   Tags: {', '.join(task['tags'])}")
                if task.get("location"):
                    formatted.append(f"   Location: {task['location']}")

            return (
                f"Found {len(tasks)} tasks:\n" + "\n".join(formatted)
            )

        except Exception as e:
            tracer = get_tracer()
            tracer.error(f"Task search failed: {e}")
            return f"Task search error: {str(e)}"
