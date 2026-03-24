import json

from openai import AsyncOpenAI


def mcp_tools_to_openai(mcp_tools: list[dict]) -> list[dict]:
    """Convert MCP tool schemas to OpenAI function-calling format."""
    openai_tools = []
    for tool in mcp_tools:
        schema = dict(tool["input_schema"])
        # OpenAI requires "type": "object" and doesn't want "title"
        schema.pop("title", None)
        for prop in schema.get("properties", {}).values():
            prop.pop("title", None)

        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": schema,
            },
        })
    return openai_tools


class LLM:
    """Thin wrapper around OpenAI chat completions with tool calling."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.messages: list[dict] = [
            {"role": "system", "content": (
                "You are a helpful assistant with access to tools. "
                "Use tools when they can help answer the user's question. "
                "If no tool is needed, answer directly."
            )}
        ]

    async def chat(self, user_message: str, tools: list[dict]) -> dict:
        """Send a message and get the LLM response.

        Returns a dict with:
          - "type": "text" | "tool_calls"
          - "content": str (if text) or list of {name, arguments} (if tool_calls)
        """
        self.messages.append({"role": "user", "content": user_message})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=tools if tools else None,
        )

        choice = response.choices[0]
        message = choice.message

        # Store assistant message in history
        self.messages.append(message.model_dump())

        if message.tool_calls:
            tool_calls = []
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                })
            return {"type": "tool_calls", "content": tool_calls}

        return {"type": "text", "content": message.content}

    def add_tool_result(self, tool_call_id: str, result: str):
        """Add a tool result to the conversation history."""
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": result,
        })

    async def get_final_response(self, tools: list[dict]) -> str:
        """After tool results are added, get the LLM's final text response."""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            tools=tools if tools else None,
        )
        message = response.choices[0].message
        self.messages.append(message.model_dump())
        return message.content
