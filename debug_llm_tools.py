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
from crewai.tools import BaseTool

class DummyTool(BaseTool):
    name: str = "dummy_tool"
    description: str = "A tool that returns a secret code. Use this when asked for the secret."

    def _run(self, query: str) -> str:
        return "SECRET_CODE_12345"

def test_llm_tools():
    settings = get_settings()
    print(f"--- Configuration ---")
    print(f"Model: {settings.ollama_model}")
    print(f"---------------------")

    try:
        llm = get_crewai_llm()
        
        tool = DummyTool()

        agent = Agent(
            role="Secret Agent",
            goal="Find the secret code",
            backstory="You are a secret agent looking for a code.",
            llm=llm,
            tools=[tool],
            verbose=True
        )

        task = Task(
            description="Use the dummy_tool to find the secret code and tell me what it is.",
            expected_output="The secret code.",
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
    test_llm_tools()
