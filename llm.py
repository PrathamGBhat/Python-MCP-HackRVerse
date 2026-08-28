import os
import json
from typing import Any, Dict, List, Optional

from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Global config
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

SYSTEM_PROMPT = """You are PyRef, a Python reference assistant for a competitive programming contest.

The contestants are Class 12 students with a CBSE-level Python background. Help them understand Python and GENERAL programming concepts so they can solve problems themselves.

ALLOWED:
- Explain Python syntax, built-in functions, data structures, and standard libraries.
- Explain general techniques such as dictionaries for frequency counting, sets for unique elements, two pointers, prefix sums, stacks, queues, binary search, sorting, etc.
- Explain when a technique is GENERALLY useful.
- Give small, generic Python examples.
- Explain basic Python errors and syntax issues.
- Use the documentation fetch tool when official Python documentation is useful.

CONTEST BOUNDARY:
Do NOT solve, analyze, or derive solutions for a specific contest problem.
Do NOT provide problem-specific algorithms, pseudocode, complete solutions, or solution code.
Do NOT tell the contestant exactly which techniques to combine or how to apply them to their problem.
Do NOT debug code if doing so would reveal the solution.

If given a specific contest problem, redirect to general concepts.

Example:
User: "I need to keep track of how many times each value occurs."
Allowed: "A dictionary is commonly used for frequency counting."

User: "Here is my problem. Should I use a dictionary?"
Do not decide for them. Explain dictionaries generally instead.

Keep responses concise, beginner-friendly, and focused on giving contestants tools to experiment with their own logic.

Think of yourself as a PYTHON/CONCEPT REFERENCE, not a solution generator.
"""


async def get_response_async(
    user_message: str,
    history: Optional[List[Dict[str, Any]]] = None,
    mcp_client: Any = None,
) -> str:
    api_key = os.environ.get("GROQ_API_KEY") or GROQ_API_KEY
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set in environment variables.")

    client = Groq(api_key=api_key)

    messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history or [])
    messages.append({"role": "user", "content": user_message})

    tools = None
    if mcp_client and hasattr(mcp_client, "get_groq_tools"):
        groq_tools = mcp_client.get_groq_tools()
        if groq_tools:
            tools = groq_tools

    # Multi-turn tool execution loop (up to 4 turns max)
    max_turns = 4
    for turn in range(max_turns):
        kwargs: Dict[str, Any] = {
            "model": GROQ_MODEL,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 1000,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        chat_completion = client.chat.completions.create(**kwargs)
        response_message = chat_completion.choices[0].message

        # Check if LLM wants to execute tool calls
        if hasattr(response_message, "tool_calls") and response_message.tool_calls and mcp_client:
            # Append LLM response (with tool_calls) to message history
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

            # Execute tool calls via MCP client
            for tool_call in response_message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    tool_args = json.loads(tool_call.function.arguments)
                except Exception:
                    tool_args = {}

                print(f"[llm.py] Groq requested tool call: {tool_name} with args {tool_args}")
                tool_result = await mcp_client.call_tool(tool_name, tool_args)

                # Truncate content if too long for token context
                if len(tool_result) > 4000:
                    tool_result = tool_result[:4000] + "\n\n...[Truncated official documentation for length]..."

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })

            # Disable further tool calls so model synthesizes final answer
            tools = None
            continue

        # No tool calls made; return final LLM response
        content = response_message.content
        if not content or not content.strip():
            raise RuntimeError("The model returned an empty response.")
        return content

    raise RuntimeError("Reached maximum tool execution turns without final response.")


def get_response(
    user_message: str,
    history: Optional[List[Dict[str, Any]]] = None,
    mcp_client: Any = None,
) -> str:
    """Synchronous wrapper for get_response_async."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(get_response_async(user_message, history, mcp_client))
    else:
        return asyncio.run(get_response_async(user_message, history, mcp_client))