import os
import json
import asyncio
import logging
from typing import Any, Dict, List, Optional

from groq import Groq
from dotenv import load_dotenv

from guardrails import REFUSAL, rule_blocked

load_dotenv()
logger = logging.getLogger("groq_api")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
GUARD_MODEL = os.environ.get("GUARD_MODEL", "qwen/qwen3.8-27b")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set in environment variables.")

client = Groq(api_key=GROQ_API_KEY)

DEFAULT_SYSTEM_PROMPT = (
    "You are PyRef, a Python reference tool for competitive programmers. Only explain "
    "Python syntax, built-ins and standard library modules with short generic examples. "
    "Refuse to solve specific problems, give their code, approach or hints, or interpret "
    "pasted problem statements."
)
# An empty or missing SYSTEM_PROMPT falls back to a safe default.
SYSTEM_PROMPT = os.environ.get("SYSTEM_PROMPT") or DEFAULT_SYSTEM_PROMPT

QUESTION_GUARD = (
    "You filter requests for a Python reference tool. Answer with ONE word: BLOCK or ALLOW.\n"
    "BLOCK: the user wants a solution, code, approach or hint for a specific algorithmic, "
    "LeetCode, Codeforces or interview problem, or pasted a problem statement.\n"
    "ALLOW: the user asks about Python syntax, a built-in, a standard library function or "
    "module, or a general concept, without applying it to solve a specific problem."
)

REPLY_GUARD = (
    "Does the following reply contain code or steps that solve a specific algorithmic, "
    "LeetCode or contest problem (not just a generic syntax example)? "
    "Answer with ONE word: YES or NO."
)


def _ask_guard(system: str, text: str) -> Optional[str]:
    """One-word guard call. Returns uppercase text, or None if the call failed."""
    try:
        r = client.chat.completions.create(
            model=GUARD_MODEL,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": text}],
            temperature=0,
            max_tokens=10,
        )
        return (r.choices[0].message.content or "").strip().upper()
    except Exception as err:
        logger.warning("Guard call failed (treating as blocked): %s", err)
        return None


def question_allowed(text: str) -> bool:
    out = _ask_guard(QUESTION_GUARD, text)
    return out is not None and out.startswith("ALLOW")      # anything else = block


def reply_allowed(reply: str) -> bool:
    out = _ask_guard(REPLY_GUARD, reply[:3000])
    return out is not None and out.startswith("NO")         # anything else = block


async def get_response_async(
    user_message: str,
    history: Optional[List[Dict[str, Any]]] = None,
    mcp_client: Any = None,
) -> str:
    history = history or []

    # NEW: check the new message together with the previous user message,
    # so a problem can't be split across two turns.
    last_user = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
    check_text = f"{last_user}\n{user_message}".strip()

    # NEW: Layer 1 (rules)
    if rule_blocked(check_text):
        logger.info("BLOCKED by rules: %r", user_message)
        return REFUSAL

    # NEW: Layer 2 (AI classifier, in a thread so the event loop isn't blocked)
    if not await asyncio.to_thread(question_allowed, check_text):
        logger.info("BLOCKED by classifier: %r", user_message)
        return REFUSAL

    messages: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    tools = None
    if mcp_client and hasattr(mcp_client, "get_groq_tools"):
        groq_tools = mcp_client.get_groq_tools()
        if groq_tools:
            tools = groq_tools

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

        # Run the blocking Groq call in a thread
        chat_completion = await asyncio.to_thread(
            client.chat.completions.create, **kwargs
        )
        response_message = chat_completion.choices[0].message

        if getattr(response_message, "tool_calls", None) and mcp_client:
            messages.append({
                "role": "assistant",
                "content": response_message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name,
                                     "arguments": tc.function.arguments},
                    }
                    for tc in response_message.tool_calls
                ],
            })

            for tc in response_message.tool_calls:
                try:
                    tool_args = json.loads(tc.function.arguments)
                except Exception:
                    tool_args = {}

                logger.info("Groq requested tool call: %s with args %s",
                            tc.function.name, tool_args)
                tool_result = await mcp_client.call_tool(tc.function.name, tool_args)

                if len(tool_result) > 4000:
                    tool_result = tool_result[:4000] + "\n\n...[Truncated response]..."

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_result,
                })

            # If this was the last allowed turn, prompt model for final response directly
            if turn == max_turns - 1:
                logger.info("Reached turn limit; requesting final synthesis from model.")
                messages.append({
                    "role": "system",
                    "content": "You have fetched sufficient documentation. Provide your final reference response to the user now. Do not call any further tools.",
                })
                final_completion = await asyncio.to_thread(
                    client.chat.completions.create,
                    model=GROQ_MODEL,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=1000,
                )
                content = final_completion.choices[0].message.content or ""
                if content.strip():
                    if "```" in content or "def " in content:
                        if not await asyncio.to_thread(reply_allowed, content):
                            logger.info("BLOCKED by reply check")
                            return REFUSAL
                    return content

            continue

        content = response_message.content
        if not content or not content.strip():
            raise RuntimeError("The model returned an empty response.")

        # NEW: Layer 3 (reply check), only when the reply looks like it has code
        if "```" in content or "def " in content:
            if not await asyncio.to_thread(reply_allowed, content):
                logger.info("BLOCKED by reply check")
                return REFUSAL

        return content

    raise RuntimeError("Reached maximum tool execution turns without final response.")
