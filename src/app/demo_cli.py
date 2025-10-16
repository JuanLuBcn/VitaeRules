#!/usr/bin/env python
"""CLI demo to test the Capture Crew interactively.

This allows you to test the Capture Crew without needing Telegram.
Run with: python -m app.demo_cli
"""

import asyncio

from app.config import get_settings
from app.contracts.plan import IntentType, Plan, PlanEntities, ToolAction
from app.crews.capture.crew import CaptureContext, CaptureCrew
from app.memory.api import MemoryService
from app.tools.list_tool import ListTool
from app.tools.registry import get_registry
from app.tools.task_tool import TaskTool
from app.tools.temporal_tool import TemporalTool
from app.tracing import get_tracer

logger = get_tracer()


def register_all_tools():
    """Register all available tools."""
    settings = get_settings()
    registry = get_registry()

    # Register tools
    task_tool = TaskTool()
    list_tool = ListTool()
    temporal_tool = TemporalTool()

    registry.register(task_tool)
    registry.register(list_tool)
    registry.register(temporal_tool)

    logger.info(f"Registered {len(registry.list_tools())} tools")


async def simulate_plan_from_input(user_input: str) -> Plan:
    """Simulate plan generation from user input.

    In a real implementation, this would use the LLM.
    For now, we do simple keyword matching.
    """
    user_input_lower = user_input.lower()

    # Detect intent from keywords
    if "task" in user_input_lower or "todo" in user_input_lower:
        if "create" in user_input_lower or "add" in user_input_lower:
            # Extract title (simplified)
            title = user_input.replace("create task", "").replace("add task", "").strip()
            if not title:
                title = "New task"

            return Plan(
                intent=IntentType.TASK_CREATE,
                entities=PlanEntities(title=title),
                actions=[
                    ToolAction(
                        tool="task_tool",
                        params={"operation": "create_task", "title": title},
                    )
                ],
                confidence=0.9,
            )

    elif "list" in user_input_lower:
        if "create" in user_input_lower:
            # Extract list name
            name = (
                user_input.replace("create list", "")
                .replace("make list", "")
                .strip()
            )
            if not name:
                name = "New List"

            return Plan(
                intent=IntentType.LIST_CREATE,
                entities=PlanEntities(list_name=name),
                actions=[
                    ToolAction(
                        tool="list_tool",
                        params={"operation": "create_list", "name": name},
                    )
                ],
                confidence=0.9,
            )
        elif "add" in user_input_lower:
            # Add item to list
            parts = user_input.split(" to ")
            if len(parts) == 2:
                item = parts[0].replace("add", "").strip()
                list_name = parts[1].strip()

                return Plan(
                    intent=IntentType.LIST_ADD,
                    entities=PlanEntities(list_name=list_name, items=[item]),
                    actions=[
                        ToolAction(
                            tool="list_tool",
                            params={
                                "operation": "add_item",
                                "list_name": list_name,
                                "item": item,
                            },
                        )
                    ],
                    confidence=0.8,
                )

    # Default: unknown intent
    return Plan(
        intent=IntentType.UNKNOWN,
        confidence=0.0,
        reasoning=f"Could not understand: {user_input}",
    )


async def interactive_demo():
    """Run an interactive CLI demo."""
    print("\n" + "=" * 60)
    print("🤖 VitaeRules Capture Crew - CLI Demo")
    print("=" * 60)
    print("\nWelcome! This is a simplified demo of the Capture Crew.")
    print("\nTry these commands:")
    print("  • create task Review PR")
    print("  • create list Shopping")
    print("  • add milk to Shopping")
    print("  • list tasks")
    print("  • quit")
    print("\n" + "=" * 60 + "\n")

    # Initialize
    register_all_tools()
    memory_service = MemoryService()
    crew = CaptureCrew(memory_service=memory_service)

    context = CaptureContext(
        chat_id="cli_demo",
        user_id="demo_user",
        auto_approve=True,  # Auto-approve for demo
    )

    registry = get_registry()

    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit", "q"]:
                print("\n👋 Goodbye!\n")
                break

            # Special commands for listing
            if user_input.lower() == "list tasks":
                task_tool = registry.get("task_tool")
                result = await task_tool.execute(
                    {"operation": "list_tasks", "user_id": "demo_user"}
                )
                if result.get("tasks"):
                    print("\n📋 Your tasks:")
                    for task in result["tasks"]:
                        status = "✅" if task["completed"] else "⬜"
                        print(f"  {status} {task['title']}")
                else:
                    print("\n📋 No tasks yet!")
                print()
                continue

            # Generate plan
            plan = await simulate_plan_from_input(user_input)

            if plan.intent == IntentType.UNKNOWN:
                print(f"\n❓ Sorry, I don't understand: {user_input}")
                print(
                    "Try: 'create task <title>' or 'create list <name>' or 'add <item> to <list>'\n"
                )
                continue

            # Execute plan
            print(f"\n💭 Understood: {plan.intent}")

            if plan.actions:
                from app.crews.capture.tool_caller import execute_plan_actions

                results = await execute_plan_actions(
                    plan=plan,
                    chat_id=context.chat_id,
                    user_id=context.user_id,
                    auto_approve=True,
                )

                # Show results
                for result in results:
                    if result.is_success():
                        print(f"✅ Success! {result.data}")
                    else:
                        print(f"❌ Error: {result.error}")
            else:
                print("⚠️  No actions to execute")

            print()

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            logger.exception("Demo error")


def main():
    """Entry point."""
    try:
        asyncio.run(interactive_demo())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
