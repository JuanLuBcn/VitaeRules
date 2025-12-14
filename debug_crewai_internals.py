import os
import sys
from typing import Any, cast
from crewai import LLM
from crewai.tools import BaseTool
import litellm
from litellm import ModelResponse, Choices

# Monkeypatch to inspect internals
def debug_call(self, *args, **kwargs):
    print(f"DEBUG: Inside LLM.call. Stream={self.stream}", file=sys.stderr)
    return LLM.call_original(self, *args, **kwargs)

LLM.call_original = LLM.call
LLM.call = debug_call

def debug_handle(self, params, callbacks=None, available_functions=None, from_task=None, from_agent=None):
    print("\n--- DEBUG: Inside _handle_non_streaming_response ---", file=sys.stderr)

    
    try:
        response = litellm.completion(**params)
        print("DEBUG: LiteLLM completion returned.", file=sys.stderr)
    except Exception as e:
        print(f"DEBUG: LiteLLM completion failed: {e}", file=sys.stderr)
        raise e

    response_message = cast(Choices, cast(ModelResponse, response).choices)[0].message
    text_response = response_message.content or ""
    
    print(f"DEBUG: text_response = '{text_response}'", file=sys.stderr)
    
    tool_calls = getattr(response_message, "tool_calls", [])
    print(f"DEBUG: tool_calls = {tool_calls}", file=sys.stderr)
    print(f"DEBUG: available_functions = {available_functions}", file=sys.stderr)

    # --- 5) If no tool calls or no available functions, return the text response directly as long as there is a text response
    if (not tool_calls or not available_functions) and text_response:
        print("DEBUG: Hit Condition 5 -> Returning text_response", file=sys.stderr)
        return text_response

    # --- 6) If there is no text response, no available functions, but there are tool calls, return the tool calls
    if tool_calls and not available_functions and not text_response:
        print("DEBUG: Hit Condition 6 -> Returning tool_calls", file=sys.stderr)
        return tool_calls

    # --- 7) Handle tool calls if present
    print("DEBUG: Proceeding to _handle_tool_call...", file=sys.stderr)
    tool_result = self._handle_tool_call(
        tool_calls, available_functions, from_task, from_agent
    )
    if tool_result is not None:
        return tool_result
    
    print("DEBUG: Fallthrough -> Returning text_response", file=sys.stderr)
    return text_response

LLM._handle_non_streaming_response = debug_handle

# Setup
llm = LLM(
    model="openai/gpt-oss:20b-cloud",
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

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

print("Running Debug Test...", file=sys.stderr)
try:
    result = llm.call(messages, tools=tools)
    print(f"RESULT: {result}", file=sys.stderr)
except Exception as e:
    print(f"Caught error: {e}", file=sys.stderr)
