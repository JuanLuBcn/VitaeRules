import os
import sys
import json
from dotenv import load_dotenv
from litellm import completion

# Load environment variables
load_dotenv()

def test_tool_calling():
    model = os.getenv("OLLAMA_MODEL", "gpt-oss:20b-cloud")
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    print(f"--- Testing Tool Calling ---")
    print(f"Model: {model}")
    print(f"Base URL: {base_url}")
    print(f"----------------------------")

    # Define a simple tool
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
        {"role": "user", "content": "What is the weather in London today?"}
    ]

    try:
        print("\nSending request to LLM...")
        response = completion(
            model=f"ollama/{model}",
            api_base=base_url,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        print("\n--- RAW RESPONSE ---")
        print(response)
        print("--------------------")

        message = response.choices[0].message
        if message.tool_calls:
            print("\n✅ SUCCESS: The model generated a tool call!")
            for tool_call in message.tool_calls:
                print(f"Function: {tool_call.function.name}")
                print(f"Arguments: {tool_call.function.arguments}")
        else:
            print("\n❌ FAILURE: The model did NOT generate a tool call.")
            print(f"Content received: {message.content}")

    except Exception as e:
        print(f"\n!!! ERROR !!!\n{e}")

if __name__ == "__main__":
    test_tool_calling()
