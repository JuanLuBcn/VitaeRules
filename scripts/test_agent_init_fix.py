"""Quick test to verify agent initialization fix."""

import asyncio
from app.llm import LLMService
from app.memory import MemoryService
from app.agents.orchestrator import AgentOrchestrator


async def test_list_agent_initialization():
    """Test that ListAgent is properly initialized with ListTool."""
    llm = LLMService()
    memory = MemoryService()
    
    orchestrator = AgentOrchestrator(llm, memory)
    
    # Test adding items to list
    result = await orchestrator.handle_message(
        message="Añade leche a la lista de la compra",
        chat_id="test_123",
        user_id="test_user"
    )
    
    print(f"✅ Result: {result['message']}")
    print(f"✅ Needs confirmation: {result['needs_confirmation']}")
    
    # Verify the agent has the correct tool
    from app.agents import IntentType
    list_agent = orchestrator.agents[IntentType.LIST]
    
    print(f"\n✅ ListAgent.list_tool type: {type(list_agent.list_tool)}")
    print(f"✅ ListAgent has execute method: {hasattr(list_agent.list_tool, 'execute')}")
    
    # Test confirmation
    if result["needs_confirmation"]:
        confirm_result = await orchestrator.handle_message(
            message="sí",
            chat_id="test_123",
            user_id="test_user"
        )
        print(f"\n✅ After confirmation: {confirm_result['message']}")


if __name__ == "__main__":
    asyncio.run(test_list_agent_initialization())
