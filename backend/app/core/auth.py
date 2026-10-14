from dataclasses import dataclass
from functools import lru_cache
import logging

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.core.config import settings

logger = logging.getLogger(__name__)

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    clerk_id: str
    email: str | None = None
    full_name: str | None = None


@lru_cache
def jwks_client() -> PyJWKClient:
    return PyJWKClient(settings.clerk_jwks_url, cache_jwk_set=True, lifespan=3600)


async def get_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required", headers={"WWW-Authenticate": "Bearer"})
    try:
        key = jwks_client().get_signing_key_from_jwt(credentials.credentials).key
        claims = jwt.decode(
            credentials.credentials,
            key,
            algorithms=["RS256"],
            issuer=settings.clerk_issuer.rstrip("/"),
            options={"require": ["exp", "iat", "sub"]},
            leeway=30,
        )
    except (jwt.PyJWTError, Exception) as exc:
        # JWKS network/key errors are also treated as invalid credentials, never trusted.
        logger.warning("Clerk token validation failed: %s", type(exc).__name__, exc_info=True)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session") from exc
    clerk_id = claims.get("sub")
    if not isinstance(clerk_id, str) or not clerk_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session subject")
    email = claims.get("email")
    name = claims.get("name")
    logger.info("Clerk principal authenticated clerk_user_id=%s", clerk_id)
    return Principal(clerk_id, email if isinstance(email, str) else None, name if isinstance(name, str) else None)
