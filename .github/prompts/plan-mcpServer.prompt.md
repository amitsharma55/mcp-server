## Plan: MCP Server — Local-First with JWT Auth

Build a Python MCP server using the official `mcp` SDK with Streamable HTTP transport, HS256 JWT authentication, sample tools (weather + bitcoin price), containerized for local use (optionally exposable via Cloudflare Tunnel or deployable to Cloud Run).

---

### Architecture

- **MCP Server**: `mcp` Python SDK (FastMCP) + Starlette, Streamable HTTP at `POST /mcp`
- **Auth**: HS256 JWT — self-signed tokens via a local script, validated by the server
- **Tools**: `@mcp.tool()` decorator with type hints → auto JSON Schema for `tools/list`
- **Run**: Local (`uvicorn`) or Docker; optionally expose via `cloudflared tunnel`

---

### Steps

**Phase 1: Project Scaffold**
1. Create `pyproject.toml` — deps: `mcp[cli]`, `httpx`, `pyjwt`, `uvicorn`
2. Create project structure under `src/` with tools, auth, config modules

**Phase 2: Auth (JWT HS256)**
3. `src/config.py` — Pydantic Settings loading env vars (`JWT_SECRET`)
4. `src/auth.py` — `TokenVerifier` subclass: decode HS256 JWT via PyJWT, validate `exp`/`sub`
5. Wire auth into FastMCP via `token_verifier=` parameter

**Phase 3: Tools**
6. `src/tools/weather.py` — `get_weather(city: str)` → calls Open-Meteo free API via httpx (no key needed)
7. `src/tools/crypto.py` — `get_bitcoin_price(currency: str = "usd")` → calls CoinGecko free API (no key needed)
8. Register tools in `server.py` with `@mcp.tool()` decorators

**Phase 4: Server Entry Point**
9. `src/server.py` — FastMCP in **stateless HTTP mode**, mount at `/mcp` on Starlette, add `/health` endpoint

**Phase 5: Token Generation**
10. `scripts/generate_token.py` — CLI script to mint HS256 JWTs signed with `JWT_SECRET`

**Phase 6: Containerization**
11. `Dockerfile` — Multi-stage, `python:3.12-slim`, non-root user, uvicorn on port 8000
12. `.env.example` — Document all required env vars

---

### Key Decisions
- **Local-first** — start/stop as needed, no cloud costs
- **HS256 JWT** — self-signed tokens, zero external dependencies (can upgrade to RS256/Auth0 later)
- **Stateless HTTP** — no session state, works across restarts
- **JSON responses** (not SSE) — simpler for agent consumption
- **No Kubernetes** — overkill for personal use; Docker optional, Cloud Run or Fly.io if cloud needed
- **CoinGecko** and **Open-Meteo** need no API keys

---

### Verification
1. `uv run uvicorn src.server:app --port 8000` — start server
2. `curl http://localhost:8000/health` → 200
3. `python scripts/generate_token.py` → JWT token
4. `curl -X POST http://localhost:8000/mcp -H "Authorization: Bearer <token>"` → tools list; without token → 401
5. `uv run mcp dev src/server.py` — test with MCP Inspector
6. `docker build -t mcp-server . && docker run -p 8000:8000 --env-file .env mcp-server` — verify container

---

### Optional: Expose to Internet
- `cloudflared tunnel --url http://localhost:8000` → public HTTPS URL, no account needed
- Or deploy to **Cloud Run**: `gcloud run deploy mcp-server --source . --allow-unauthenticated`
