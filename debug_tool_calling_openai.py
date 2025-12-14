import os
from litellm import completion
import json

# Define the tool schema
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather in a given location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and state, e.g. San Francisco, CA",
                    },
                    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
                },
                "required": ["location"],
            },
        },
    }
]

messages = [
    {"role": "user", "content": "What is the weather in Madrid?"}
]

print("Testing Raw LiteLLM with OpenAI Provider -> Ollama...")

try:
    response = completion(
        model="openai/gpt-oss:20b-cloud",
        api_key="ollama",
        base_url="http://localhost:11434/v1",
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )

    print("\nResponse:\n", response)

    if response.choices[0].message.tool_calls:
        print("\n✅ SUCCESS: The model generated a tool call!")
        for tool_call in response.choices[0].message.tool_calls:
            print(f"Function: {tool_call.function.name}")
            print(f"Arguments: {tool_call.function.arguments}")
    else:
        print("\n❌ FAILURE: No tool call generated.")
        print("Content:", response.choices[0].message.content)

except Exception as e:
    print(f"\n❌ ERROR: {e}")
