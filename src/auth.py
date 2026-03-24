import jwt
from mcp.server.auth.provider import TokenVerifier, AccessToken

from src.config import settings


class JWTVerifier(TokenVerifier):
    """Validates HS256 JWT tokens signed with JWT_SECRET."""

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=["HS256"],
            )
            return AccessToken(
                token=token,
                client_id=payload.get("sub", "anonymous"),
                scopes=payload.get("scopes", []),
            )
        except jwt.InvalidTokenError:
            return None
