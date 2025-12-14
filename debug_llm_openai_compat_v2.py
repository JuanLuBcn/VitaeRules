import os
from crewai import Agent, Task, Crew, LLM
from crewai.tools import BaseTool
import litellm

# ENABLE DEEP DEBUGGING
litellm.set_verbose = True
os.environ["LITELLM_LOG"] = "DEBUG"

# 1. Define the tool using CrewAI's BaseTool
class WeatherTool(BaseTool):
    name: str = "get_weather"
    description: str = "Get the weather for a specific city. Input should be the city name."

    def _run(self, city: str) -> str:
        return f"The weather in {city} is Sunny and 25°C"

# 2. Configure LLM using OpenAI protocol pointing to local Ollama
llm = LLM(
    model="openai/gpt-oss:20b-cloud",
    base_url="http://localhost:11434/v1",
    api_key="ollama",
    temperature=0
)

# 3. Create Agent
agent = Agent(
    role="Weather Reporter",
    goal="Report the weather",
    backstory="You are a helpful assistant.",
    llm=llm,
    tools=[WeatherTool()],
    verbose=True
)

# 4. Create Task
task = Task(
    description="What is the weather in Madrid? You MUST use the get_weather tool.",
    expected_output="The weather report.",
    agent=agent
)

# 5. Run
print("Starting CrewAI with OpenAI-Compat configuration...")
crew = Crew(agents=[agent], tasks=[task])
result = crew.kickoff()
print("\nFINAL RESULT:", result)
