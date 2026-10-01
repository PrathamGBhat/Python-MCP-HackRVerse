import sys
import logging
from typing import Any, Dict, List, Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger("fetch_mcp")


class FetchMCP:
    """
    Class to handle lifecycle of ClientSession objects from mcp

    Attributes:
        session - MCP client session
        tools - List of tools defined by MCP binaries
        _exit_stack - Stack to gracefully handle the context of multiple async functions

    Methods:
        initialize()
        get_groq_tools()
        call_tool()
        close()
    """

    def __init__(self):
        self.session: Optional[ClientSession] = None
        self._exit_stack: Optional[AsyncExitStack] = None
        self.tools: List[Any] = []

    async def initialize(self):
        """Launches mcp-server-fetch subprocess and initializes MCP session."""

        if self.session is not None:
            return

        logger.info("Initializing mcp-server-fetch via stdio...")

        # Configure parameters for mcp client
        server_params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server_fetch"],
            env=None,
        )
        self._exit_stack = AsyncExitStack()

        try:

            # Connect stdio streams of client and server to finally create an mcp client object
            stdio_transport = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read_stream, write_stream = stdio_transport

            self.session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await self.session.initialize()

            # Discover and assign available tools to self.tools
            response = await self.session.list_tools()
            self.tools = response.tools
            tool_names = [t.name for t in self.tools]

            logger.info("Successfully connected. Available tools: %s", tool_names)

        except Exception as err:
            logger.error("Failed to initialize: %s", err)
            await self.close()
            raise err

    def get_groq_tools(self) -> List[Dict[str, Any]]:
        """Return tools in OpenAI/Groq payload format"""

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
            raise RuntimeError("FetchMCP session is not initialized.")

        logger.info("Calling tool '%s' with args: %s", name, arguments)

        # Call tool and return response
        result = await self.session.call_tool(name, arguments)
        text_contents = []
        for item in result.content:
            if hasattr(item, "text"):
                text_contents.append(item.text)
            else:
                text_contents.append(str(item))

        return "\n\n".join(text_contents)

    async def close(self):
        """Gracefully closes MCP session and sub-process"""

        if self._exit_stack:
            try:
                await self._exit_stack.aclose()
            except Exception as err:
                logger.error("Error during shutdown: %s", err)
            finally:
                self._exit_stack = None
                self.session = None
                logger.info("Closed MCP session cleanly.")
