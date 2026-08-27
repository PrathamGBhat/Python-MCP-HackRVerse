import os
import sys
import asyncio

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp_client import MCPClient

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


async def main():
    print("=== Running Phase 2 Tests ===")
    client = MCPClient()

    # Test 2.1 & 2.2: Initialization & Tool Discovery
    await client.initialize()
    tool_names = [t.name for t in client.tools]
    print(f"[Test 2.1 & 2.2 PASS] Subprocess connected & tools listed: {tool_names}")

    groq_tools = client.get_groq_tools()
    print(f"[Test 2.2 PASS] Formatted {len(groq_tools)} tool(s) for Groq schema.")

    # Test 2.3: Online Docs Retrieval via fetch tool
    test_url = "https://docs.python.org/3/library/heapq.html"
    print(f"[Test 2.3] Executing fetch tool on {test_url}...")
    result = await client.call_tool("fetch", {"url": test_url})

    print("\n--- Fetched Documentation Snippet (First 500 chars) ---")
    print(result[:500])
    print("----------------------------------------------------\n")

    if not result or len(result) == 0:
        raise ValueError("Fetched result is empty!")
    if "heapq" not in result.lower():
        raise ValueError("Fetched content does not contain expected 'heapq' keyword.")
    
    print("[Test 2.3 PASS] Successfully fetched and validated official heapq documentation.")

    # Test 2.4: Graceful Shutdown
    await client.close()
    print("[Test 2.4 PASS] Closed session and subprocess cleanly.")
    print("\n=== Phase 2 Tests PASSED ===")


if __name__ == "__main__":
    asyncio.run(main())
