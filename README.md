# MCP Server + AI Agent

A Python MCP server with JWT authentication and sample tools (weather + Bitcoin price), plus an AI agent that uses OpenAI to reason about and call those tools.

## Architecture

```
User prompt → OpenAI GPT-4o (decides tool calls) → MCP Client → MCP Server (localhost:8000)
                    ↑                                    ↓
                    └──────── tool results ──────────────┘
```

- **MCP Server**: `mcp` Python SDK (FastMCP) + Starlette, Streamable HTTP at `POST /mcp`
- **Auth**: HS256 JWT — self-signed tokens, validated by the server
- **Tools**: Auto-discovered via MCP protocol — add tools to the server, agent sees them automatically
- **Agent**: Interactive CLI that connects to the MCP server and uses OpenAI for reasoning

## Project Structure

```
mcp-server/
├── pyproject.toml
├── Dockerfile
├── .env.example
├── .env                        ← your secrets (git-ignored)
├── scripts/
│   └── generate_token.py       ← mint JWT tokens
├── src/                        ← MCP Server
│   ├── __init__.py
│   ├── config.py               ← loads env vars
│   ├── auth.py                 ← HS256 JWT verifier
│   ├── server.py               ← FastMCP + Starlette app
│   └── tools/
│       ├── __init__.py
│       ├── weather.py          ← Open-Meteo weather tool
│       └── crypto.py           ← CoinGecko Bitcoin price tool
└── agent/                      ← AI Agent
    ├── __init__.py
    ├── mcp_client.py           ← connects to MCP server
    ├── llm.py                  ← OpenAI integration
    └── main.py                 ← interactive CLI
```

---

## Prerequisites

| Tool | Install |
|---|---|
| Python 3.12+ | `brew install python@3.12` |
| uv (package manager) | `brew install uv` |
| Docker (optional) | Docker Desktop for Mac |

## Setup

### 1. Install dependencies

```bash
cd /path/to/mcp-server
uv sync
```

This installs all Python packages (`mcp`, `httpx`, `pyjwt`, `uvicorn`, `openai`, etc.) into a local `.venv`.

### 2. Create your `.env` file

```bash
cp .env.example .env
```

### 3. Generate a JWT secret

```bash
openssl rand -hex 32
```

Paste the output as `JWT_SECRET` in `.env`.

### 4. Generate a JWT token

```bash
uv run python scripts/generate_token.py
```

This prints a JWT token valid for 30 days. Paste it as `MCP_TOKEN` in `.env`.

Options:
```bash
uv run python scripts/generate_token.py --sub amit --days 60
```

### 5. Add your API keys to `.env`

```
JWT_SECRET=<from step 3>
MCP_SERVER_URL=http://localhost:8000/mcp
MCP_TOKEN=<from step 4>
OPENAI_API_KEY=<your OpenAI API key>
```

---

## MCP Server

### Start the server

```bash
uv run uvicorn src.server:app --port 8000
```

The server runs at `http://localhost:8000`. Press `Ctrl+C` to stop.

### Test the server

#### Health check

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`

#### Test unauthenticated access (should be blocked)

```bash
curl -s -w "\nHTTP %{http_code}\n" -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

Expected: `401 Unauthorized`

#### Test authenticated access

```bash
TOKEN=$(uv run python scripts/generate_token.py)

# Initialize
curl -s -X POST http://localhost:8000/mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | python3 -m json.tool
```

Expected: JSON with `protocolVersion`, `capabilities`, and `serverInfo`.

#### List tools

```bash
curl -s -X POST http://localhost:8000/mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":2}' | python3 -m json.tool
```

Expected: Two tools — `get_weather` and `get_bitcoin_price` with their input schemas.

#### Call the Bitcoin price tool

```bash
curl -s -X POST http://localhost:8000/mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/call","id":3,"params":{"name":"get_bitcoin_price","arguments":{"currency":"usd"}}}' | python3 -m json.tool
```

Expected: Current Bitcoin price in USD.

#### Call the weather tool (needs API key)

```bash
curl -s -X POST http://localhost:8000/mcp \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/call","id":4,"params":{"name":"get_weather","arguments":{"city":"London"}}}' | python3 -m json.tool
```

The weather tool uses the free [Open-Meteo API](https://open-meteo.com/) — no API key required.

---

## AI Agent

The agent connects to the MCP server, auto-discovers tools, and uses OpenAI GPT-4o to decide when to call them.

### Run the agent

Make sure the MCP server is running first (in a separate terminal), then:

```bash
uv run python -m agent.main
```

Expected output:

```
Connecting to MCP server...
Connected to: MCP Server v1.26.0
Available tools: get_weather, get_bitcoin_price

Type your question (or 'quit' to exit):
```

### Example prompts

| Prompt | What happens |
|---|---|
| `What's the Bitcoin price?` | Agent calls `get_bitcoin_price` → returns price |
| `What is Bitcoin trading at in EUR?` | Agent calls `get_bitcoin_price(currency="eur")` |
| `What's the weather in London?` | Agent calls `get_weather(city="London")` (needs API key) |
| `What's 2 + 2?` | Agent answers directly — no tool call |
| `quit` | Exits the agent |

Tool calls are visible in real time:

```
You: What's the Bitcoin price?
  → Calling get_bitcoin_price({"currency": "usd"})
  ← Result received
Assistant: Bitcoin is at $70,487 USD, up 3.3% in the last 24h.
```

---

## Docker (Optional)

### Build and run

```bash
docker build -t mcp-server .
docker run -p 8000:8000 --env-file .env mcp-server
```

This builds a container image and runs the server on port 8000. The `--env-file .env` passes your secrets into the container.

### Test

Same curl commands as above — the server is at `http://localhost:8000`.

---

## Expose to Internet (Optional)

### Cloudflare Tunnel (no account needed)

```bash
brew install cloudflared
cloudflared tunnel --url http://localhost:8000
```

This gives you a public `https://*.trycloudflare.com` URL. No signup required. Stop with `Ctrl+C`.

### Cloud Run (Google Cloud)

```bash
gcloud run deploy mcp-server --source . --allow-unauthenticated
```

One command deploy. Tear down with:

```bash
gcloud run services delete mcp-server
```

---

## Adding New Tools

1. Create a new file in `src/tools/` (e.g. `src/tools/my_tool.py`)
2. Write an async function with type hints and a docstring:

```python
async def my_tool(param: str) -> dict:
    """Description shown to the LLM."""
    return {"result": "..."}
```

3. Register it in `src/server.py`:

```python
from src.tools.my_tool import my_tool
mcp.tool()(my_tool)
```

4. Restart the server — the agent auto-discovers the new tool on next startup.
