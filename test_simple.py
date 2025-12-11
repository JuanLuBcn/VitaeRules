"""Simple test for CrewAI agents without Unicode."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app.llm import get_llm_service, get_crewai_llm
from app.memory import MemoryService
from app.crews.retrieval import RetrievalCrew, RetrievalContext

def main():
    print("="*60)
    print("Testing CrewAI Agent Initialization")
    print("="*60)
    
    try:
        # Test 1: Create services
        print("\n1. Creating services...")
        llm_service = get_llm_service()
        memory_service = MemoryService()
        print("   OK: Services created")
        
        # Test 2: Get CrewAI LLM
        print("\n2. Getting CrewAI LLM...")
        crewai_llm = get_crewai_llm(llm_service)
        print(f"   OK: CrewAI LLM created: {type(crewai_llm)}")
        
        # Test 3: Create crew
        print("\n3. Creating RetrievalCrew...")
        crew = RetrievalCrew(memory_service, llm_service)
        print(f"   OK: Crew created, agents initialized: {crew._agents_initialized}")
        
        # Test 4: Initialize agents
        print("\n4. Initializing agents...")
        crew._initialize_agents()
        print(f"   OK: Agents initialized: {crew._agents_initialized}")
        print(f"   - QueryPlanner: {crew.query_planner_agent is not None}")
        print(f"   - Retriever: {crew.retriever_agent is not None}")
        print(f"   - Composer: {crew.composer_agent is not None}")
        print(f"   - Crew: {crew._crew is not None}")
        
        # Test 5: Run retrieval
        print("\n5. Testing retrieval...")
        context = RetrievalContext(
            chat_id="test",
            user_id="test",
            memory_service=memory_service
        )
        result = crew.retrieve("What did I tell you about Maria?", context)
        print(f"   OK: Retrieval completed")
        print(f"   - Memories found: {len(result.memories)}")
        print(f"   - Answer: {result.answer.answer[:100]}")
        
        print("\n" + "="*60)
        print("SUCCESS: All tests passed!")
        print("="*60)
        return 0
        
    except Exception as e:
        print(f"\nFAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
