"""
Test CrewAI memory sharing with crew.kickoff()

This tests the retrieve_with_crew_tasks() method which uses full CrewAI
orchestration with shared memory between agents.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app.llm import get_llm_service
from app.memory import MemoryService
from app.crews.retrieval import RetrievalCrew, RetrievalContext

def test_crewai_memory_sharing():
    print("="*70)
    print("Testing CrewAI Memory Sharing with crew.kickoff()")
    print("="*70)
    
    try:
        # Setup
        print("\n1. Setting up services...")
        llm_service = get_llm_service()
        memory_service = MemoryService()
        crew = RetrievalCrew(memory_service, llm_service)
        print("   OK: Services created")
        
        # Create test context
        context = RetrievalContext(
            chat_id="test_chat",
            user_id="test_user",
            memory_service=memory_service
        )
        
        # Test question
        question = "What did I tell you about Maria?"
        print(f"\n2. Test question: '{question}'")
        
        # Run with CrewAI tasks (full orchestration)
        print("\n3. Running retrieve_with_crew_tasks()...")
        print("   This will:")
        print("   - Initialize agents (if not already done)")
        print("   - Create tasks for each agent")
        print("   - Run crew.kickoff() with shared memory")
        print("   - Agents will see each other's outputs via CrewAI memory")
        print()
        
        result = crew.retrieve_with_crew_tasks(question, context)
        
        print("\n" + "="*70)
        print("SUCCESS: CrewAI orchestration completed!")
        print("="*70)
        
        # Display results
        print(f"\nQuery created:")
        print(f"  - Text: {result.query.query_text}")
        print(f"  - Intent: {result.query.intent.value}")
        print(f"  - Reasoning: {result.query.reasoning}")
        
        print(f"\nMemories found: {len(result.memories)}")
        if result.memories:
            for i, mem in enumerate(result.memories[:3], 1):
                print(f"  {i}. {mem.content[:80]}...")
        
        print(f"\nAnswer generated:")
        print(f"  {result.answer.answer[:200]}...")
        
        # Check CrewAI memory location
        print("\n" + "="*70)
        print("Checking CrewAI Memory Files")
        print("="*70)
        
        import appdirs
        crew_dir = appdirs.user_data_dir("crewAI")
        print(f"\nCrewAI data directory: {crew_dir}")
        
        if os.path.exists(crew_dir):
            print("Directory contents:")
            for root, dirs, files in os.walk(crew_dir):
                level = root.replace(crew_dir, '').count(os.sep)
                indent = ' ' * 2 * level
                print(f'{indent}{os.path.basename(root)}/')
                sub_indent = ' ' * 2 * (level + 1)
                for file in files[:5]:  # Limit to first 5 files per dir
                    file_path = os.path.join(root, file)
                    size = os.path.getsize(file_path)
                    print(f'{sub_indent}{file} ({size} bytes)')
        else:
            print("Directory does not exist yet")
        
        print("\n" + "="*70)
        print("TEST PASSED: CrewAI memory sharing works!")
        print("="*70)
        
        return True
        
    except Exception as e:
        print("\n" + "="*70)
        print("TEST FAILED")
        print("="*70)
        print(f"\nError: {e}")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()
        
        return False

if __name__ == "__main__":
    success = test_crewai_memory_sharing()
    sys.exit(0 if success else 1)
