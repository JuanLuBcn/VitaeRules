from crewai import LLM
import inspect

print(f"LLM Class: {LLM}")
print(f"LLM Module: {LLM.__module__}")
print(f"LLM File: {inspect.getfile(LLM)}")

llm = LLM(model="gpt-3.5-turbo", api_key="na")
print(f"Instance type: {type(llm)}")

# Check if we can patch instance
def my_call(self, *args, **kwargs):
    print("PATCHED CALL")
    return "PATCHED"

llm.call = my_call.__get__(llm, LLM)
print(f"Call result: {llm.call('hi')}")
