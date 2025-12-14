import os
from crewai import LLM

# Configure LLM
llm = LLM(
    model="openai/gpt-oss:20b-cloud",
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

print("LLM Methods:", dir(llm))

print("Testing CrewAI LLM wrapper directly...")

try:
    # Test 1: Simple generation
    print("\n--- Test 1: Simple Generation ---")
    messages = [{"role": "user", "content": "Say hello!"}]
    # CrewAI's LLM class usually has a call method or similar. 
    # It wraps LiteLLM, so let's try to see what methods it has or just call it.
    # Based on recent CrewAI versions, it might be .call()
    response = llm.call(messages)
    print("Response:", response)

except Exception as e:
    print(f"Error in Test 1: {e}")

try:
    # Test 2: Tool calling (simulated)
    print("\n--- Test 2: Tool Calling ---")
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get weather",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {"type": "string"}
                    },
                    "required": ["location"]
                }
            }
        }
    ]
    messages = [{"role": "user", "content": "What is the weather in London?"}]
    # Pass tools to the call. Note: The argument name might be 'tools' or 'functions' depending on implementation
    # We will try 'tools' as per OpenAI standard which LiteLLM uses.
    response = llm.call(messages, tools=tools)
    print(f"Response type: {type(response)}")
    print(f"Response: {response}")

except Exception as e:
    print(f"Error in Test 2: {e}")
