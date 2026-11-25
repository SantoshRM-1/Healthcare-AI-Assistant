import logging
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient, PyJWKClientError

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
    except PyJWKClientError as exc:
        logger.warning("Clerk signing-key lookup unavailable: %s", type(exc).__name__)
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Authentication verification is temporarily unavailable",
        ) from exc
    except jwt.PyJWTError as exc:
        logger.warning("Clerk token validation failed: %s", type(exc).__name__)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired session",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    clerk_id = claims.get("sub")
    if not isinstance(clerk_id, str) or not clerk_id:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid session subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email = claims.get("email")
    name = claims.get("name")
    logger.debug("Clerk principal authenticated")
    return Principal(clerk_id, email if isinstance(email, str) else None, name if isinstance(name, str) else None)


def is_knowledge_admin(clerk_id: str) -> bool:
    """Fail-closed allow-list gate; Clerk metadata alone cannot grant approval rights."""
    allowed_ids = {clerk_id.strip() for clerk_id in settings.knowledge_admin_clerk_ids.split(",") if clerk_id.strip()}
    return bool(allowed_ids and clerk_id in allowed_ids)


async def require_knowledge_admin(principal: Principal = Depends(get_principal)) -> Principal:
    if not is_knowledge_admin(principal.clerk_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Medical knowledge administration is not authorized")
    return principal
