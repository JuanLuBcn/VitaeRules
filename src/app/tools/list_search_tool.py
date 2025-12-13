"""List Search Tool for CrewAI agents."""

from typing import Optional, Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool as CrewAIBaseTool

from app.tools.list_tool import ListTool
from app.tracing import get_tracer


class ListSearchToolSchema(BaseModel):
    """Input schema for ListSearchTool."""

    search_query: Optional[str] = Field(
        default=None,
        description="Keywords to search for in list names and item contents"
    )
    list_name: Optional[str] = Field(
        default=None,
        description="Optional: specific list name to search within. Leave empty to search all lists"
    )


class ListSearchTool(CrewAIBaseTool):
    """Tool for searching lists and list items."""

    name: str = "list_search"
    description: str = (
        "Search and list all lists and their items. Use this tool to find "
        "shopping lists, todo lists, or any collection of items. "
        "User context is automatically included."
    )
    args_schema: Type[BaseModel] = ListSearchToolSchema
    
    # Use class attributes to avoid Pydantic validation
    _list_tool: ListTool | None = None
    _user_id: str = "default"
    _chat_id: str = "default"

    def __init__(
        self, 
        list_tool: ListTool | None = None,
        user_id: str = "default",
        chat_id: str = "default"
    ):
        """Initialize List Search Tool.

        Args:
            list_tool: List tool instance (default: create new)
            user_id: User identifier to store in context
            chat_id: Chat identifier to store in context
        """
        super().__init__()
        # Store in class attributes to avoid Pydantic validation
        ListSearchTool._list_tool = list_tool or ListTool()
        ListSearchTool._user_id = user_id
        ListSearchTool._chat_id = chat_id
        tracer = get_tracer()
        tracer.debug(f"ListSearchTool initialized with user_id={user_id}, chat_id={chat_id}")

    def _run(
        self,
        search_query: str | None = None,
        list_name: str | None = None,
    ) -> str:
        """Search lists and items synchronously.

        Args:
            search_query: Optional text to search in list names and item content
            list_name: Optional specific list name to filter by

        Returns:
            Formatted list of lists with their items
        
        Note: user_id and chat_id are taken from the tool's stored context
        """
        tracer = get_tracer()
        
        # Handle case where LLM outputs array instead of dict
        if isinstance(search_query, list):
            tracer.warning(f"Received array for 'search_query': {search_query}, extracting first element")
            search_query = search_query[0] if len(search_query) > 0 and isinstance(search_query[0], str) else None
        
        if isinstance(list_name, list):
            tracer.warning(f"Received array for 'list_name': {list_name}, extracting first element")
            list_name = list_name[0] if len(list_name) > 0 and isinstance(list_name[0], str) else None
        
        try:
            # Get all lists
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            lists_result = loop.run_until_complete(
                ListSearchTool._list_tool.execute({
                    "operation": "get_lists",
                    "user_id": self._user_id,
                    "chat_id": self._chat_id,
                })
            )

            if "error" in lists_result:
                return f"List search error: {lists_result['error']}"

            lists = lists_result.get("lists", [])

            # Filter by list name if provided
            if list_name:
                list_name_lower = list_name.lower()
                lists = [l for l in lists if list_name_lower in l.get("name", "").lower()]

            if not lists:
                return "No lists found matching the criteria."

            # Get items for each list
            all_results = []
            for list_obj in lists:
                list_id = list_obj["id"]
                list_display_name = list_obj["name"]

                # Get items for this list
                items_result = loop.run_until_complete(
                    ListSearchTool._list_tool.execute({
                        "operation": "list_items",
                        "list_id": list_id,
                    })
                )

                items = items_result.get("items", [])

                # Filter items by search query if provided
                if search_query and items:
                    search_lower = search_query.lower()
                    filtered_items = [
                        item for item in items
                        if search_lower in item.get("text", "").lower()
                        or search_lower in list_display_name.lower()
                    ]
                    # Only include list if it has matching items or matching name
                    if filtered_items or search_lower in list_display_name.lower():
                        items = filtered_items
                    else:
                        continue

                all_results.append({
                    "list": list_obj,
                    "items": items
                })

            if not all_results:
                return "No lists or items found matching the search query."

            # Format results
            formatted = []
            for result in all_results:
                list_obj = result["list"]
                items = result["items"]

                formatted.append(f"\n**{list_obj['name']}** ({len(items)} items)")

                if items:
                    for i, item in enumerate(items, 1):
                        status = "✓" if item.get("completed") else "○"
                        formatted.append(f"   {i}. [{status}] {item['text']}")

                        # Add optional fields
                        if item.get("people"):
                            formatted.append(f"      People: {', '.join(item['people'])}")
                        if item.get("tags"):
                            formatted.append(f"      Tags: {', '.join(item['tags'])}")
                        if item.get("location"):
                            formatted.append(f"      Location: {item['location']}")
                        if item.get("notes"):
                            formatted.append(f"      Notes: {item['notes']}")
                else:
                    formatted.append("   (empty list)")

            return (
                f"Found {len(all_results)} lists:\n" + "\n".join(formatted)
            )

        except Exception as e:
            tracer = get_tracer()
            tracer.error(f"List search failed: {e}")
            return f"List search error: {str(e)}"
