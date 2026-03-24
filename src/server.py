import contextlib

from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings

from src.auth import JWTVerifier
from src.tools.weather import get_weather
from src.tools.crypto import get_bitcoin_price

mcp = FastMCP(
    "MCP Server",
    stateless_http=True,
    json_response=True,
    token_verifier=JWTVerifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl("http://localhost:8000"),
        resource_server_url=AnyHttpUrl("http://localhost:8000"),
        required_scopes=[],
    ),
)

# Register tools
mcp.tool()(get_weather)
mcp.tool()(get_bitcoin_price)


async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "ok"})


@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    async with mcp.session_manager.run():
        yield


app = Starlette(
    routes=[
        Route("/health", health),
        Mount("/", app=mcp.streamable_http_app()),
    ],
    lifespan=lifespan,
)
