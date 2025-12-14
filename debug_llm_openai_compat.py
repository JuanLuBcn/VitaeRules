import os
from crewai import Agent, Task, Crew, LLM
from langchain.tools import tool

# 1. Define the tool
@tool
def get_weather(city: str):
    """Get the weather for a specific city."""
    return f"The weather in {city} is Sunny and 25°C"

# 2. Configure LLM using OpenAI protocol pointing to local Ollama
# We use "openai/" prefix to tell LiteLLM/CrewAI to use the OpenAI client
# We point base_url to the Ollama API
llm = LLM(
    model="openai/gpt-oss:20b-cloud",
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # Required but ignored by Ollama
    temperature=0
)

# 3. Create Agent
agent = Agent(
    role="Weather Reporter",
    goal="Report the weather",
    backstory="You are a helpful assistant.",
    llm=llm,
    tools=[get_weather],
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
