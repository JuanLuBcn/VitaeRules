"""ListTool for managing lists and items."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..config import get_settings
from ..contracts import BaseTool
from ..tracing import get_tracer


class ListTool(BaseTool):
    """
    Tool for managing lists and list items.

    Operations:
    - create_list: Create a new list
    - delete_list: Delete a list and all its items
    - add_item: Add an item to a list
    - remove_item: Remove an item from a list
    - complete_item: Mark an item as complete
    - list_items: Get all items in a list
    - get_lists: Get all lists
    """

    def __init__(self, db_path: Path | None = None):
        """
        Initialize ListTool.

        Args:
            db_path: Path to SQLite database (default: from settings)
        """
        self.settings = get_settings()
        self.tracer = get_tracer()
        self.db_path = db_path or self.settings.storage_path / "lists.sqlite"

        self._init_db()
        self.tracer.debug(f"ListTool initialized at {self.db_path}")

    def _init_db(self) -> None:
        """Initialize the database schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lists (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    user_id TEXT,
                    chat_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS list_items (
                    id TEXT PRIMARY KEY,
                    list_id TEXT NOT NULL,
                    text TEXT NOT NULL,
                    completed INTEGER DEFAULT 0,
                    position INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    FOREIGN KEY (list_id) REFERENCES lists(id) ON DELETE CASCADE
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_list_user ON lists(user_id, chat_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_item_list ON list_items(list_id, position)"
            )
            conn.commit()

    @property
    def name(self) -> str:
        """Tool name."""
        return "list_tool"

    @property
    def description(self) -> str:
        """Tool description."""
        return (
            "Manage lists and list items. Operations: create_list, delete_list, "
            "add_item, remove_item, complete_item, list_items, get_lists"
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
                        "create_list",
                        "delete_list",
                        "add_item",
                        "remove_item",
                        "complete_item",
                        "list_items",
                        "get_lists",
                    ],
                    "description": "Operation to perform",
                },
                "list_name": {
                    "type": "string",
                    "description": "Name of the list (for create_list, delete_list, add_item, list_items)",
                },
                "list_id": {
                    "type": "string",
                    "description": "ID of the list (alternative to list_name)",
                },
                "item_text": {
                    "type": "string",
                    "description": "Text of the item (for add_item)",
                },
                "item_id": {
                    "type": "string",
                    "description": "ID of the item (for remove_item, complete_item)",
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
        """Execute the list operation."""
        operation = arguments["operation"]

        if operation == "create_list":
            return await self._create_list(arguments)
        elif operation == "delete_list":
            return await self._delete_list(arguments)
        elif operation == "add_item":
            return await self._add_item(arguments)
        elif operation == "remove_item":
            return await self._remove_item(arguments)
        elif operation == "complete_item":
            return await self._complete_item(arguments)
        elif operation == "list_items":
            return await self._list_items(arguments)
        elif operation == "get_lists":
            return await self._get_lists(arguments)
        else:
            raise ValueError(f"Unknown operation: {operation}")

    async def _create_list(self, args: dict[str, Any]) -> dict[str, Any]:
        """Create a new list."""
        list_name = args.get("list_name")
        if not list_name:
            raise ValueError("list_name is required for create_list")

        user_id = args.get("user_id")
        chat_id = args.get("chat_id")

        list_id = str(uuid4())
        now = datetime.now(UTC).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO lists (id, name, user_id, chat_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (list_id, list_name, user_id, chat_id, now, now),
            )
            conn.commit()

        self.tracer.info(f"Created list: {list_name} (id={list_id})")

        return {
            "list_id": list_id,
            "list_name": list_name,
            "created_at": now,
        }

    async def _delete_list(self, args: dict[str, Any]) -> dict[str, Any]:
        """Delete a list and all its items."""
        list_id = await self._resolve_list_id(args)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT name FROM lists WHERE id = ?", (list_id,))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"List not found: {list_id}")

            list_name = row[0]

            conn.execute("DELETE FROM lists WHERE id = ?", (list_id,))
            conn.commit()

        self.tracer.info(f"Deleted list: {list_name} (id={list_id})")

        return {
            "list_id": list_id,
            "list_name": list_name,
            "deleted": True,
        }

    async def _add_item(self, args: dict[str, Any]) -> dict[str, Any]:
        """Add an item to a list."""
        # Try to resolve list ID, auto-create if not found
        try:
            list_id = await self._resolve_list_id(args)
        except ValueError as e:
            # List doesn't exist - auto-create it
            list_name = args.get("list_name")
            if not list_name:
                raise ValueError(f"Cannot add item: {str(e)}")
            
            self.tracer.info(f"Auto-creating list: {list_name}")
            create_result = await self._create_list(args)
            list_id = create_result["list_id"]
        
        item_text = args.get("item_text")
        if not item_text:
            raise ValueError("item_text is required for add_item")

        with sqlite3.connect(self.db_path) as conn:
            # Get next position
            cursor = conn.execute(
                "SELECT MAX(position) FROM list_items WHERE list_id = ?", (list_id,)
            )
            max_pos = cursor.fetchone()[0]
            position = (max_pos or 0) + 1

            item_id = str(uuid4())
            now = datetime.now(UTC).isoformat()

            conn.execute(
                """
                INSERT INTO list_items (id, list_id, text, position, created_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (item_id, list_id, item_text, position, now),
            )

            # Update list timestamp
            conn.execute(
                "UPDATE lists SET updated_at = ? WHERE id = ?", (now, list_id)
            )
            conn.commit()

        self.tracer.debug(f"Added item to list {list_id}: {item_text}")

        return {
            "item_id": item_id,
            "item_text": item_text,
            "list_id": list_id,
            "position": position,
        }

    async def _remove_item(self, args: dict[str, Any]) -> dict[str, Any]:
        """Remove an item from a list."""
        item_id = args.get("item_id")
        if not item_id:
            raise ValueError("item_id is required for remove_item")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT text, list_id FROM list_items WHERE id = ?", (item_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Item not found: {item_id}")

            item_text, list_id = row

            conn.execute("DELETE FROM list_items WHERE id = ?", (item_id,))

            # Update list timestamp
            now = datetime.now(UTC).isoformat()
            conn.execute(
                "UPDATE lists SET updated_at = ? WHERE id = ?", (now, list_id)
            )
            conn.commit()

        self.tracer.debug(f"Removed item {item_id} from list {list_id}")

        return {
            "item_id": item_id,
            "item_text": item_text,
            "removed": True,
        }

    async def _complete_item(self, args: dict[str, Any]) -> dict[str, Any]:
        """Mark an item as complete."""
        item_id = args.get("item_id")
        if not item_id:
            raise ValueError("item_id is required for complete_item")

        now = datetime.now(UTC).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT text, list_id FROM list_items WHERE id = ?", (item_id,)
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Item not found: {item_id}")

            item_text, list_id = row

            conn.execute(
                "UPDATE list_items SET completed = 1, completed_at = ? WHERE id = ?",
                (now, item_id),
            )

            # Update list timestamp
            conn.execute(
                "UPDATE lists SET updated_at = ? WHERE id = ?", (now, list_id)
            )
            conn.commit()

        self.tracer.debug(f"Completed item {item_id} in list {list_id}")

        return {
            "item_id": item_id,
            "item_text": item_text,
            "completed": True,
            "completed_at": now,
        }

    async def _list_items(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get all items in a list."""
        list_id = await self._resolve_list_id(args)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT id, text, completed, position, created_at, completed_at
                FROM list_items
                WHERE list_id = ?
                ORDER BY position
            """,
                (list_id,),
            )
            items = [dict(row) for row in cursor.fetchall()]

        return {
            "list_id": list_id,
            "items": items,
            "count": len(items),
        }

    async def _get_lists(self, args: dict[str, Any]) -> dict[str, Any]:
        """Get all lists for a user/chat."""
        user_id = args.get("user_id")
        chat_id = args.get("chat_id")

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            query = "SELECT id, name, created_at, updated_at FROM lists"
            params = []

            if user_id or chat_id:
                conditions = []
                if user_id:
                    conditions.append("user_id = ?")
                    params.append(user_id)
                if chat_id:
                    conditions.append("chat_id = ?")
                    params.append(chat_id)
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY updated_at DESC"

            cursor = conn.execute(query, params)
            lists = [dict(row) for row in cursor.fetchall()]

        return {
            "lists": lists,
            "count": len(lists),
        }

    async def _resolve_list_id(self, args: dict[str, Any]) -> str:
        """
        Resolve list ID from either list_id or list_name.

        Args:
            args: Arguments dict

        Returns:
            List ID

        Raises:
            ValueError: If list cannot be found
        """
        list_id = args.get("list_id")
        if list_id:
            return list_id

        list_name = args.get("list_name")
        if not list_name:
            raise ValueError("Either list_id or list_name is required")

        # Normalize list name (case-insensitive lookup)
        normalized_name = list_name.strip().lower()

        # Look up by name (case-insensitive)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id FROM lists WHERE LOWER(name) = ?", (normalized_name,)
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"List not found: {list_name}")
            return row[0]
