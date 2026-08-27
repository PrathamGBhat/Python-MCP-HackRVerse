import sys
from typing import Any, Dict, List, Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self._exit_stack: Optional[AsyncExitStack] = None
        self.tools: List[Any] = []

    async def initialize(self):
        """Launches mcp-server-fetch subprocess and initializes MCP session."""
        print("[MCPClient] Initializing mcp-server-fetch via stdio...")

        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server_fetch"],
            env=None,
        )

        self._exit_stack = AsyncExitStack()

        try:
            stdio_transport = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read_stream, write_stream = stdio_transport

            self.session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )

            await self.session.initialize()

            # Discover available MCP tools
            response = await self.session.list_tools()
            self.tools = response.tools
            tool_names = [t.name for t in self.tools]
            print(f"[MCPClient] Successfully connected. Available tools: {tool_names}")

        except Exception as err:
            print(f"[MCPClient] Failed to initialize: {err}")
            await self.close()
            raise err

    def get_groq_tools(self) -> List[Dict[str, Any]]:
        """Transforms MCP tool schemas to OpenAI/Groq function calling payload format."""
        groq_tools = []
        for tool in self.tools:
            groq_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "Fetch content from a URL as Markdown",
                    "parameters": tool.inputSchema,
                },
            })
        return groq_tools

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Executes a tool call on the MCP server and returns text result."""
        if not self.session:
            raise RuntimeError("MCPClient session is not initialized.")

        print(f"[MCPClient] Calling tool '{name}' with args: {arguments}")
        result = await self.session.call_tool(name, arguments)
        
        text_contents = []
        for item in result.content:
            if hasattr(item, "text"):
                text_contents.append(item.text)
            else:
                text_contents.append(str(item))

        return "\n\n".join(text_contents)

    async def close(self):
        """Gracefully closes MCP session and sub-process."""
        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except Exception as err:
                pass
            finally:
                self._exit_stack = None
                self.session = None
                print("[MCPClient] Closed MCP session cleanly.")
