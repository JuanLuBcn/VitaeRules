import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from app.config import get_settings
from app.llm.crewai_llm import get_crewai_llm
from crewai import Agent, Task, Crew

def test_llm():
    settings = get_settings()
    print(f"--- Configuration ---")
    print(f"Backend: {settings.llm_backend}")
    print(f"Base URL: {settings.ollama_base_url}")
    print(f"Model: {settings.ollama_model}")
    print(f"---------------------")

    try:
        print("\n1. Initializing LLM...")
        llm = get_crewai_llm()
        print("   Success!")

        print("\n2. Creating Test Agent...")
        agent = Agent(
            role="Debug Agent",
            goal="Say hello",
            backstory="You are a debug agent.",
            llm=llm,
            verbose=True
        )
        print("   Success!")

        print("\n3. Running Test Task...")
        task = Task(
            description="Say 'Hello, I am working!' and nothing else.",
            expected_output="A simple greeting.",
            agent=agent
        )

        crew = Crew(
            agents=[agent],
            tasks=[task],
            verbose=True
        )

        result = crew.kickoff()
        print(f"\n--- RESULT ---\n{result}\n--------------")

    except Exception as e:
        print(f"\n!!! ERROR !!!\n{e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_llm()
