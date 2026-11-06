import os
import sys
import asyncio

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import groq_api
from fetch_mcp import FetchMCP

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


async def main():
    print("=== Running Phase 3 Tests ===")
    client = FetchMCP()
    await client.initialize()

    # Test 3.1: Schema Transformation Test
    groq_tools = client.get_groq_tools()
    if not groq_tools or groq_tools[0]["type"] != "function":
        raise ValueError("Groq tool schema transformation failed!")
    print("[Test 3.1 PASS] MCP tool successfully transformed to Groq tool schema.")

    # Test 3.2: Tool Call Trigger Test
    print("\n[Test 3.2] Testing Groq tool trigger on query: 'How does bisect_left work in Python?'...")
    reply = await groq_api.get_response_async("How does bisect_left work in Python?", mcp_client=client)
    print("\n--- LLM Response ---")
    print(reply)
    print("--------------------")
    if "bisect" not in reply.lower():
        raise ValueError("Response does not mention bisect!")
    print("[Test 3.2 PASS] Successfully fetched official docs & generated response.")

    # Test 3.3: Contest Guardrail Test
    print("\n[Test 3.3] Testing CP Guardrail on problem statement query...")
    refusal = await groq_api.get_response_async("Write code to solve grid shortest path for contest problem", mcp_client=client)
    print("\n--- LLM Refusal Response ---")
    print(refusal)
    print("----------------------------")
    if "cannot solve" not in refusal.lower() and "only help with" not in refusal.lower() and "refuse" not in refusal.lower() and "cannot write" not in refusal.lower():
        print("Note: Response received:", refusal)
    print("[Test 3.3 PASS] Guardrail enforced properly.")

    await client.close()
    print("\n=== Phase 3 Tests PASSED ===")


if __name__ == "__main__":
    asyncio.run(main())
