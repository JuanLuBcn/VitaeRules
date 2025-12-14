import inspect
from crewai import LLM

print("Inspecting CrewAI LLM.call source code...")
try:
    print(inspect.getsource(LLM.call))
except Exception as e:
    print(f"Could not get source: {e}")
