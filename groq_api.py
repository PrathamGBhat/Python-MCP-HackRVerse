import os
import re
import json
import asyncio
import logging
from typing import Any, Dict, List, Optional

from groq import Groq
from dotenv import load_dotenv

from guardrails import REFUSAL, rule_blocked
from complexity_data import lookup_complexity

load_dotenv()
logger = logging.getLogger("groq_api")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
GUARD_MODEL = os.environ.get("GUARD_MODEL", "qwen/qwen3.8-27b")

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set in environment variables.")

client = Groq(api_key=GROQ_API_KEY)

DEFAULT_SYSTEM_PROMPT = (
    "You are PyRef, a Python reference tool for competitive programmers. You explain "
    "Python syntax, built-ins, standard library modules, and general programming concepts "
    "using short generic 3-5 line examples with made-up data. When asked about algorithm types "
    "or concepts (e.g. sorting algorithms), clearly distinguish between what is NATIVELY BUILT INTO "
    "Python (e.g., Timsort in list.sort() and sorted(), Heapsort in heapq) versus classic textbook "
    "algorithms (e.g., Bubble Sort, Selection Sort, Insertion Sort, Merge Sort, Quick Sort) which are "
    "NOT built into Python and must be written manually. Briefly contrast their Big-O complexities and "
    "highlight CP TLE pitfalls (e.g., Bubble/Selection Sort are O(N^2) and will TLE for N > 1000). "
    "STRICT RULES: 1. NEVER USE MARKDOWN TABLES (| col | col |). Do not generate tables under any circumstances. "
    "Present all comparisons, data structures, and references using clear headings, bullet points, and "
    "standard code blocks with proper line breaks. 2. Refuse to solve specific problems, give their code, "
    "approach or hints, or interpret pasted problem statements. When refusing, offer to explain a relevant "
    "Python function instead. 3. At the very end of your response, provide a structured complexity block in this "
    "exact format:\n"
    ":::complexity\n"
    "time: <Big-O time complexity, e.g. O(N log N)>\n"
    "space: <Big-O auxiliary space, e.g. O(N)>\n"
    "safe_n: <Maximum safe N for 1.0s limit, e.g. N <= 10^6>\n"
    "pitfall: <1-2 sentences on CP pitfalls or TLE dangers, or None>\n"
    ":::"
)
# An empty or missing SYSTEM_PROMPT falls back to a safe default.
SYSTEM_PROMPT = os.environ.get("SYSTEM_PROMPT") or DEFAULT_SYSTEM_PROMPT

COMPLEXITY_PATTERN = re.compile(
    r":::complexity\s*\n"
    r"time:\s*(?P<time>[^\n]+)\n"
    r"space:\s*(?P<space>[^\n]+)\n"
    r"safe_n:\s*(?P<safe_n>[^\n]+)\n"
    r"pitfall:\s*(?P<pitfall>[^\n]+)\n"
    r":::",
    re.MULTILINE | re.IGNORECASE
)

LOOSE_COMPLEXITY_PATTERN = re.compile(
    r":::complexity\s*\n(.*?):::",
    re.DOTALL | re.IGNORECASE
)


def sanitize_no_tables(text: str) -> str:
    """
    Detects any markdown tables in the response text and converts them
    into clean, readable subsections, bullet points, and proper Python code blocks.
    Fixes escaped literal '\\n' sequences inside code snippets.
    """
    if not text or "|" not in text:
        return text

    lines = text.split("\n")
    new_lines: List[str] = []
    i = 0
    in_table = False
    table_headers: List[str] = []
    table_rows: List[List[str]] = []

    def flush_table() -> List[str]:
        nonlocal in_table, table_headers, table_rows
        if not table_rows:
            in_table = False
            table_headers = []
            return []

        out: List[str] = []
        for row in table_rows:
            name = row[0] if row else "Item"
            out.append(f"\n### {name}")
            for col_idx in range(1, len(row)):
                col_name = table_headers[col_idx] if col_idx < len(table_headers) else f"Detail {col_idx}"
                val = row[col_idx].strip()
                if not val:
                    continue
                # If value contains escaped python code (like python\narr = ... or \n)
                if "\\n" in val or "python\\n" in val:
                    cleaned_code = val.replace("python\\n", "").replace("\\n", "\n").replace("`", "").strip()
                    out.append(f"- **{col_name}**:")
                    out.append("```python")
                    out.append(cleaned_code)
                    out.append("```")
                else:
                    out.append(f"- **{col_name}**: {val}")

        in_table = False
        table_headers = []
        table_rows = []
        return out

    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("|") and line.endswith("|"):
            parts = [c.strip() for c in line.strip("|").split("|")]
            # Skip separator rows like | --- | --- |
            if all(set(c).issubset({"-", ":", " "}) for c in parts if c):
                i += 1
                continue

            if not in_table:
                in_table = True
                table_headers = parts
            else:
                table_rows.append(parts)
            i += 1
        else:
            if in_table:
                new_lines.extend(flush_table())
            new_lines.append(lines[i])
            i += 1

    if in_table:
        new_lines.extend(flush_table())

    return "\n".join(new_lines)


def parse_complexity_payload(response_text: str, query: str = "") -> Dict[str, Any]:
    """
    Extracts the :::complexity block from response_text.
    Returns {"text": clean_markdown, "complexity": dict_or_none}.
    If LLM omitted the block, falls back to deterministic lookup_complexity(query).
    """
    if not response_text or response_text == REFUSAL:
        return {"text": response_text, "complexity": None}

    match = COMPLEXITY_PATTERN.search(response_text)
    if match:
        data = match.groupdict()
        clean_text = COMPLEXITY_PATTERN.sub("", response_text).strip()
        pitfall_val = data["pitfall"].strip()
        if pitfall_val.lower() in ("none", "n/a", "no pitfall", "null"):
            pitfall_val = None
        return {
            "text": sanitize_no_tables(clean_text),
            "complexity": {
                "time": data["time"].strip(),
                "space": data["space"].strip(),
                "safe_n": data["safe_n"].strip(),
                "pitfall": pitfall_val,
            }
        }

    loose_match = LOOSE_COMPLEXITY_PATTERN.search(response_text)
    if loose_match:
        block_content = loose_match.group(1)
        clean_text = LOOSE_COMPLEXITY_PATTERN.sub("", response_text).strip()
        comp_dict = {}
        for line in block_content.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                comp_dict[k.strip().lower()] = v.strip()

        if "time" in comp_dict and "space" in comp_dict:
            pitfall_val = comp_dict.get("pitfall")
            if pitfall_val and pitfall_val.lower() in ("none", "n/a", "no pitfall", "null"):
                pitfall_val = None
            return {
                "text": sanitize_no_tables(clean_text),
                "complexity": {
                    "time": comp_dict.get("time", "O(1)"),
                    "space": comp_dict.get("space", "O(1)"),
                    "safe_n": comp_dict.get("safe_n", "N <= 10^6"),
                    "pitfall": pitfall_val,
                }
            }

    # Deterministic fallback based on query keywords
    fallback = lookup_complexity(query)
    if fallback:
        return {
            "text": sanitize_no_tables(response_text.strip()),
            "complexity": fallback,
        }

    return {"text": sanitize_no_tables(response_text.strip()), "complexity": None}

QUESTION_GUARD = (
    "You filter requests for a Python reference tool. Answer with ONE word: BLOCK or ALLOW.\n"
    "BLOCK: The user pasted a problem statement, or is asking to solve a specific contest, "
    "LeetCode, or Codeforces problem or challenge (e.g. Two Sum, knapsack, shortest path in grid, "
    "coin change, maximum subarray, or any pasted contest puzzle).\n"
    "ALLOW: The user asks to explain a general Computer Science concept, data structure, syntax, "
    "or fundamental sorting/searching algorithm (e.g. explain bubble sort, how does merge sort work, "
    "binary search, selection sort, quicksort, recursion, heapq, dict, deque)."
)

REPLY_GUARD = (
    "Does the following reply solve a specific contest challenge, LeetCode problem, or pasted "
    "contest problem statement (like Two Sum, Knapsack DP, grid shortest path, N-Queens)?\n"
    "Answer YES only if it solves a specific competitive programming contest problem.\n"
    "Answer NO if it is an educational explanation of standard language syntax, data structures, "
    "or fundamental textbook sorting/searching concepts (such as bubble sort, merge sort, binary search, "
    "heapq, dict) with generic 3-5 line code.\n"
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
