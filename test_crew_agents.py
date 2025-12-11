"""
Test script to verify CrewAI agents can be instantiated and memory works.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app.llm import get_llm_service, get_crewai_llm
from app.memory import MemoryService
from app.crews.retrieval import RetrievalCrew, RetrievalContext
from app.tracing import get_tracer

tracer = get_tracer()

def test_crewai_llm():
    """Test that get_crewai_llm works."""
    print("\n" + "="*60)
    print("TEST 1: CrewAI LLM Compatibility")
    print("="*60)
    
    try:
        llm_service = get_llm_service()
        print(f"✓ LLM Service created: {llm_service}")
        
        crewai_llm = get_crewai_llm(llm_service)
        print(f"✓ CrewAI LLM extracted: {crewai_llm}")
        print(f"  Type: {type(crewai_llm)}")
        print(f"  Model: {crewai_llm.model_name if hasattr(crewai_llm, 'model_name') else 'N/A'}")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_agent_initialization():
    """Test that agents can be created with CrewAI LLM."""
    print("\n" + "="*60)
    print("TEST 2: Agent Initialization")
    print("="*60)
    
    try:
        llm_service = get_llm_service()
        memory_service = MemoryService()
        
        print("✓ Services created")
        
        # Create RetrievalCrew (lazy init - agents not created yet)
        crew = RetrievalCrew(memory_service, llm_service)
        print(f"✓ RetrievalCrew created: {crew}")
        print(f"  Agents initialized: {crew._agents_initialized}")
        
        # Force agent initialization
        print("\nInitializing agents...")
        crew._initialize_agents()
        
        print(f"✓ Agents initialized: {crew._agents_initialized}")
        print(f"  Query Planner: {crew.query_planner_agent}")
        print(f"  Retriever: {crew.retriever_agent}")
        print(f"  Composer: {crew.composer_agent}")
        print(f"  Crew: {crew._crew}")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_retrieval_workflow():
    """Test the full retrieval workflow."""
    print("\n" + "="*60)
    print("TEST 3: Retrieval Workflow (Manual)")
    print("="*60)
    
    try:
        llm_service = get_llm_service()
        memory_service = MemoryService()
        crew = RetrievalCrew(memory_service, llm_service)
        
        # Create context
        context = RetrievalContext(
            chat_id="test_chat",
            user_id="test_user",
            memory_service=memory_service
        )
        
        # Test question
        question = "What did I tell you about María?"
        print(f"\nQuestion: {question}")
        
        # Run retrieval (manual workflow - not using CrewAI tasks yet)
        print("\nRunning retrieval...")
        result = crew.retrieve(question, context)
        
        print(f"\n✓ Retrieval completed!")
        print(f"  Query: {result.query}")
        print(f"  Memories found: {len(result.memories)}")
        print(f"  Answer: {result.answer.answer[:200]}")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_crew_tasks():
    """Test CrewAI orchestration with tasks."""
    print("\n" + "="*60)
    print("TEST 4: CrewAI Task Orchestration")
    print("="*60)
    
    try:
        llm_service = get_llm_service()
        memory_service = MemoryService()
        crew = RetrievalCrew(memory_service, llm_service)
        
        # Create context
        context = RetrievalContext(
            chat_id="test_chat",
            user_id="test_user",
            memory_service=memory_service
        )
        
        # Test question
        question = "What did I tell you about María?"
        print(f"\nQuestion: {question}")
        
        # Run with CrewAI tasks
        print("\nRunning with CrewAI orchestration...")
        result = crew.retrieve_with_crew_tasks(question, context)
        
        print(f"\n✓ CrewAI orchestration completed!")
        print(f"  Query: {result.query}")
        print(f"  Memories found: {len(result.memories)}")
        print(f"  Answer: {result.answer.answer[:200]}")
        
        # Check CrewAI memory location
        import appdirs
        app_dir = appdirs.user_data_dir("CrewAI", "VitaeRules")
        print(f"\n✓ CrewAI memory location: {app_dir}")
        
        if os.path.exists(app_dir):
            print(f"  Directory exists!")
            for item in os.listdir(app_dir):
                print(f"  - {item}")
        else:
            print(f"  Directory does not exist yet")
        
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n")
    print("="*60)
    print("CrewAI Agent Testing Suite")
    print("="*60)
    
    results = {
        "LLM Compatibility": test_crewai_llm(),
        "Agent Initialization": test_agent_initialization(),
        "Manual Workflow": test_retrieval_workflow(),
        "CrewAI Orchestration": test_crew_tasks()
    }
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    print("\n" + ("="*60))
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*60 + "\n")
    
    sys.exit(0 if all_passed else 1)
