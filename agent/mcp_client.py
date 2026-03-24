import json

import httpx
from mcp.client.streamable_http import streamable_http_client
from mcp.client.session import ClientSession
from mcp.shared._httpx_utils import create_mcp_http_client


class MCPClient:
    """Connects to an MCP server over Streamable HTTP with JWT auth."""

    def __init__(self, server_url: str, token: str):
        self.server_url = server_url
        self.token = token
        self._http_client = None
        self._session: ClientSession | None = None
        self._streams_cm = None
        self._http_cm = None

    async def connect(self):
        """Establish connection to the MCP server and initialize the session."""
        headers = {"Authorization": f"Bearer {self.token}"}
        timeout = httpx.Timeout(30.0, read=300.0)
        self._http_client = create_mcp_http_client(headers=headers, timeout=timeout)
        self._http_cm = self._http_client
        await self._http_cm.__aenter__()

        self._streams_cm = streamable_http_client(
            url=self.server_url,
            http_client=self._http_client,
            terminate_on_close=True,
        )
        read_stream, write_stream, _ = await self._streams_cm.__aenter__()

        self._session = ClientSession(read_stream, write_stream)
        await self._session.__aenter__()
        init_result = await self._session.initialize()
        return init_result

    async def list_tools(self) -> list[dict]:
        """Fetch available tools from the MCP server.

        Returns a list of tool dicts with name, description, and inputSchema
        (the format needed to convert to OpenAI function-calling format).
        """
        result = await self._session.list_tools()
        tools = []
        for tool in result.tools:
            tools.append({
                "name": tool.name,
                "description": tool.description or "",
                "input_schema": tool.inputSchema,
            })
        return tools

    async def call_tool(self, name: str, arguments: dict) -> str:
        """Call a tool on the MCP server and return the text result."""
        result = await self._session.call_tool(name=name, arguments=arguments)
        texts = []
        for content in result.content:
            if hasattr(content, "text"):
                texts.append(content.text)
        return "\n".join(texts)

    async def close(self):
        """Clean up all connections."""
        if self._session:
            await self._session.__aexit__(None, None, None)
        if self._streams_cm:
            await self._streams_cm.__aexit__(None, None, None)
        if self._http_cm:
            await self._http_cm.__aexit__(None, None, None)
