#!/usr/bin/env python3
"""Interactive AI agent that uses MCP server tools via OpenAI."""

import asyncio
import os
import sys

from dotenv import load_dotenv

from agent.mcp_client import MCPClient
from agent.llm import LLM, mcp_tools_to_openai


async def run():
    load_dotenv()

    # Validate required env vars
    mcp_url = os.environ.get("MCP_SERVER_URL", "http://localhost:8000/mcp")
    mcp_token = os.environ.get("MCP_TOKEN")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if not mcp_token:
        print("Error: MCP_TOKEN not set in .env", file=sys.stderr)
        sys.exit(1)
    if not openai_key:
        print("Error: OPENAI_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    # Connect to MCP server
    print("Connecting to MCP server...")
    mcp = MCPClient(server_url=mcp_url, token=mcp_token)
    try:
        init = await mcp.connect()
        print(f"Connected to: {init.serverInfo.name} v{init.serverInfo.version}")

        # Discover tools
        mcp_tools = await mcp.list_tools()
        openai_tools = mcp_tools_to_openai(mcp_tools)
        print(f"Available tools: {', '.join(t['name'] for t in mcp_tools)}")
        print("\nType your question (or 'quit' to exit):\n")

        llm = LLM(api_key=openai_key)

        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye!")
                break

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                print("Bye!")
                break

            # Send to LLM
            response = await llm.chat(user_input, openai_tools)

            # If LLM wants to call tools, execute them
            while response["type"] == "tool_calls":
                for tc in response["content"]:
                    print(f"  → Calling {tc['name']}({tc['arguments']})")
                    result = await mcp.call_tool(tc["name"], tc["arguments"])
                    print(f"  ← Result received")
                    llm.add_tool_result(tc["id"], result)

                # Get LLM's response after tool results
                final = await llm.get_final_response(openai_tools)
                response = {"type": "text", "content": final}

            print(f"\nAssistant: {response['content']}\n")

    finally:
        await mcp.close()


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
