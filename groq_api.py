import os
import json
import logging
from typing import Any, Dict, List, Optional

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("groq_api")

# Global config
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set in environment variables.")

# Single shared Groq client — instantiated once at startup
client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = os.environ.get("SYSTEM_PROMPT", "")


async def get_response_async(
    user_message: str,
    history: Optional[List[Dict[str, Any]]] = None,
    mcp_client: Any = None,
) -> str:

    # Append history to messages
    messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history or [])
    messages.append({"role": "user", "content": user_message})

    # Extract tools to give to Groq client
    tools = None
    if mcp_client and hasattr(mcp_client, "get_groq_tools"):
        groq_tools = mcp_client.get_groq_tools()
        if groq_tools:
            tools = groq_tools

    # Tool call loop - Maximum 4 tool calls per prompt
    max_turns = 4
    for turn in range(max_turns):

        # Compile prompt and capture response
        kwargs: Dict[str, Any] = {
            "model": GROQ_MODEL,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1000,
        }
        if tools and turn < max_turns - 1: # Last response shouldn't call tools
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        chat_completion = client.chat.completions.create(**kwargs)
        response_message = chat_completion.choices[0].message

        # Handle tool calls (if any) in response
        if hasattr(response_message, "tool_calls") and response_message.tool_calls and mcp_client:

            # Append LLM response with tool calls to messages
            messages.append({
                "role": "assistant",
                "content": response_message.content or "",
                "tool_calls": [
                    {
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments,
                        },
                    }
                    for tool_call in response_message.tool_calls
                ],
            })

            # Execute tool call
            for tool_call in response_message.tool_calls:
                tool_name = tool_call.function.name

                try:
                    tool_args = json.loads(tool_call.function.arguments)
                except Exception:
                    tool_args = {}

                logger.info("Groq requested tool call: %s with args %s", tool_name, tool_args)
                tool_result = await mcp_client.call_tool(tool_name, tool_args)

                if len(tool_result) > 4000: # Truncate long responses
                    tool_result = tool_result[:4000] + "\n\n...[Truncated response]..."

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })

            continue

        # Return final LLM response after all tool calls
        content = response_message.content
        if not content or not content.strip():
            raise RuntimeError("The model returned an empty response.")
        return content

    raise RuntimeError("Reached maximum tool execution turns without final response.")