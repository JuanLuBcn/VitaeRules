"""TaskTool for managing tasks."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..config import get_settings
from ..contracts import BaseTool
from ..tracing import get_tracer


class TaskTool(BaseTool):
    """
    Tool for managing tasks.

    Operations:
    - create_task: Create a new task
    - complete_task: Mark a task as complete
    - list_tasks: Get all tasks (optionally filter by status)
    - update_task: Update task details
    - delete_task: Delete a task
    """

    def __init__(self, db_path: Path | None = None):
        """
        Initialize TaskTool.

        Args:
            db_path: Path to SQLite database (default: from settings)
        """
        self.settings = get_settings()
        self.tracer = get_tracer()
        self.db_path = db_path or self.settings.storage_path / "tasks.sqlite"

        self._init_db()
        self.tracer.debug(f"TaskTool initialized at {self.db_path}")

    def _init_db(self) -> None:
        """Initialize the database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    due_at TEXT,
                    priority INTEGER DEFAULT 0,
                    completed INTEGER DEFAULT 0,
                    user_id TEXT,
                    chat_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_task_user ON tasks(user_id, chat_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_task_due ON tasks(due_at, completed)"
            )
            conn.commit()

    @property
    def name(self) -> str:
        """Tool name."""
        return "task_tool"

    @property
    def description(self) -> str:
        """Tool description."""
        return (
            "Manage tasks with due dates and priorities. Operations: create_task, "
            "complete_task, list_tasks, update_task, delete_task"
        )

    @property
    def schema(self) -> dict[str, Any]:
        """JSON Schema for tool arguments."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": [
                        "create_task",
                        "complete_task",
                        "list_tasks",
                        "update_task",
                        "delete_task",
                    ],
                    "description": "Operation to perform",
                },
                "task_id": {
                    "type": "string",
                    "description": "ID of the task (for complete, update, delete)",
                },
                "title": {
                    "type": "string",
                    "description": "Task title (for create_task, update_task)",
                },
                "description": {
                    "type": "string",
                    "description": "Task description (optional)",
                },
                "due_at": {
                    "type": "string",
                    "description": "Due date/time in ISO format (optional)",
                },
                "priority": {
                    "type": "integer",
                    "description": "Priority level (0=low, 1=medium, 2=high, 3=urgent)",
                },
                "completed": {
                    "type": "boolean",
                    "description": "Completion status (for list_tasks filter)",
                },
                "user_id": {
                    "type": "string",
                    "description": "User identifier",
                },
                "chat_id": {
                    "type": "string",
                    "description": "Chat identifier",
                },
            },
            "required": ["operation"],
        }

    async def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute the task operation."""
        operation = arguments["operation"]

        if operation == "create_task":
            return await self._create_task(arguments)
        elif operation == "complete_task":
            return await self._complete_task(arguments)
        elif operation == "list_tasks":
            return await self._list_tasks(arguments)
        elif operation == "update_task":
            return await self._update_task(arguments)
        elif operation == "delete_task":
            return await self._delete_task(arguments)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    async def _create_task(self, args: dict[str, Any]) -> dict[str, Any]:
        """Create a new task."""
        title = args.get("title")
        if not title:
            raise ValueError("title is required for create_task")

        task_id = str(uuid4())
        now = datetime.now(UTC).isoformat()

        description = args.get("description")
        due_at = args.get("due_at")
        priority = args.get("priority", 0)
        user_id = args.get("user_id")
        chat_id = args.get("chat_id")

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO tasks (id, title, description, due_at, priority,
                                   user_id, chat_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (task_id, title, description, due_at, priority, user_id, chat_id, now, now),
            )
            conn.commit()

        self.tracer.info(f"Created task: {title} (id={task_id})")

        return {
            "task_id": task_id,
            "title": title,
            "description": description,
            "due_at": due_at,
            "priority": priority,
            "created_at": now,
        }

    async def _complete_task(self, args: dict[str, Any]) -> dict[str, Any]:
        """Mark a task as complete."""
        task_id = args.get("task_id")
        if not task_id:
            raise ValueError("task_id is required for complete_task")

        now = datetime.now(UTC).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT title FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Task not found: {task_id}")

            title = row[0]

            conn.execute(
                """
                UPDATE tasks
                SET completed = 1, completed_at = ?, updated_at = ?
                WHERE id = ?
            """,
                (now, now, task_id),
            )
            conn.commit()

        self.tracer.info(f"Completed task: {title} (id={task_id})")

        return {
            "task_id": task_id,
            "title": title,
            "completed": True,
            "completed_at": now,
        }

    async def _list_tasks(self, args: dict[str, Any]) -> dict[str, Any]:
        """List tasks with optional filtering."""
        user_id = args.get("user_id")
        chat_id = args.get("chat_id")
        completed = args.get("completed")

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = """
                SELECT id, title, description, due_at, priority,
                       completed, created_at, updated_at, completed_at
                FROM tasks
            """
            params = []
            conditions = []

            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)
            if chat_id:
                conditions.append("chat_id = ?")
                params.append(chat_id)
            if completed is not None:
                conditions.append("completed = ?")
                params.append(1 if completed else 0)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY priority DESC, due_at ASC, created_at DESC"

            cursor = conn.execute(query, params)
            tasks = [dict(row) for row in cursor.fetchall()]

        return {
            "tasks": tasks,
            "count": len(tasks),
        }

    async def _update_task(self, args: dict[str, Any]) -> dict[str, Any]:
        """Update task details."""
        task_id = args.get("task_id")
        if not task_id:
            raise ValueError("task_id is required for update_task")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,))
            if not cursor.fetchone():
                raise ValueError(f"Task not found: {task_id}")

            updates = []
            params = []

            if "title" in args:
                updates.append("title = ?")
                params.append(args["title"])
            if "description" in args:
                updates.append("description = ?")
                params.append(args["description"])
            if "due_at" in args:
                updates.append("due_at = ?")
                params.append(args["due_at"])
            if "priority" in args:
                updates.append("priority = ?")
                params.append(args["priority"])

            if not updates:
                raise ValueError("No fields to update")

            now = datetime.now(UTC).isoformat()
            updates.append("updated_at = ?")
            params.append(now)
            params.append(task_id)

            conn.execute(
                f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", params
            )
            conn.commit()

        self.tracer.debug(f"Updated task {task_id}")

        return {
            "task_id": task_id,
            "updated": True,
            "updated_at": now,
        }

    async def _delete_task(self, args: dict[str, Any]) -> dict[str, Any]:
        """Delete a task."""
        task_id = args.get("task_id")
        if not task_id:
            raise ValueError("task_id is required for delete_task")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT title FROM tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Task not found: {task_id}")

            title = row[0]

            conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()

        self.tracer.info(f"Deleted task: {title} (id={task_id})")

        return {
            "task_id": task_id,
            "title": title,
            "deleted": True,
        }
