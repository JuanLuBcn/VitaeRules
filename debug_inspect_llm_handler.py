import inspect
from crewai import LLM

print("Inspecting CrewAI LLM._handle_non_streaming_response source code...")
try:
    print(inspect.getsource(LLM._handle_non_streaming_response))
except Exception as e:
    print(f"Could not get source: {e}")
