"""Authentication and authorization for the Clause API gateway.

Implements:
- JWT bearer-token verification (authn)
- Scope-based document access control (authz)
- FastAPI dependency injection for both
"""

from __future__ import annotations
# python when loading, checks from top to bottom and panics if class if defined later but
# its type hint used earlier, so earlier dev put "type" like in string format
# python does not check this now, which saves time to boot up
# instead of doing this, just put from __future__ import annotations in every req file

from config import settings
import logging
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

JWT_ALGORITHM = settings().JWT_ALGORITHM
JWT_SECRET = settings().JWT_SECRET
TOKEN_EXPIRY_MINUTES = settings().TOKEN_EXPIRY_MINUTES
ISSUER = settings().ISSUER
_bearer_scheme = HTTPBearer()


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------
class AccessScope(StrEnum):  # now all eunum values must be string
    """Document-access scopes that map to metadata filters in retrieval."""

    LEGAL = "legal"
    COMPLIANCE = "compliance"
    PROCUREMENT = "procurement"
    ADMIN = "admin"  # can access everything


# When inherit Enum, every variable is now enum type
# s=AccesScope.NAME its an enum object, but value is string
# cant compare directly thats why used StrEnum, which is just a wrapper actual object is still enum
# print(s) gives s.value(legal) which is str, s.name is also str (LEGAL)
# s is enum class object, but now due to strEnum can be used to compare with str directly
# which in fact still possible, but static linters like ruff might not allow


class TokenPayload(BaseModel):
    """Validated claims extracted from the JWT."""

    sub: str = Field(default=..., description="User ID / email")  # ...means req field
    # field enforces extra condition
    scopes: list[AccessScope] = Field(
        description="Document scopes the user may retrieve",
    )
    exp: datetime
    iss: str


# ---------------------------------------------------------------------------
# Token creation (used by a /login or /token endpoint)
# ---------------------------------------------------------------------------
def create_access_token(
    user_id: str,
    scopes: list[AccessScope],
    *,  #  after the * args, must be explicitly named when calling the function.
    expires_delta: timedelta | None = None,
) -> str:
    """Mint a signed JWT with embedded access scopes."""
    now = datetime.now(timezone.utc)  # datetime.now() uses local time
    # also jwt compares with server utc time
    expire = now + (expires_delta or timedelta(minutes=TOKEN_EXPIRY_MINUTES))

    payload = {
        "sub": user_id,
        "scopes": [s.value for s in scopes],
        "exp": expire,
        "iat": now,  # issued at
        "iss": ISSUER,
    }
    # jwt library when decode, looks for certain names predrefined like
    # sub,exp,iat,iss(issuer) changing these we lose native automation features
    # like exp check, hash check
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    logger.info("Token issued for user=%s scopes=%s", user_id, scopes)
    return token


# ---------------------------------------------------------------------------
# Token verification (FastAPI dependency)
# ---------------------------------------------------------------------------
def _decode_token(raw_token: str) -> TokenPayload:
    """Decode + validate JWT; raises HTTPException on any failure."""

    # --- PHASE 1: CRYPTOGRAPHIC DECODING ---
    try:
        data = jwt.decode(
            raw_token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],  # very imp, if not provide attacks possible
            issuer=ISSUER,
        )
    except jwt.ExpiredSignatureError:
        logger.warning("Expired token presented")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidIssuedAtError:
        logger.warning("Token issued date is in the future (skewed clock)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token execution lifecycle invalid",
        )
    except jwt.InvalidIssuerError:
        logger.warning("Cross-environment or invalid issuer detected")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token source origin",
        )
    except jwt.InvalidTokenError as exc:
        logger.warning("Cryptographic verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    # --- PHASE 2: STRUCTURAL VALIDATION (Outside the JWT Try Block) ---
    try:
        # If keys are missing, KeyError triggers here.
        # If AccessScope mapping fails, ValueError triggers here.
        return TokenPayload(
            sub=data["sub"],
            scopes=[AccessScope(s) for s in data.get("scopes", [])],
            # .get(value to search, default)
            # imp but not here some external auth providers when issue token
            # leaves those fields in payloads which are empty so there if
            # i write my another decoder without .get it would fail-> defensive engineering
            exp=datetime.fromtimestamp(data["exp"], tz=timezone.utc),
            # converts to datetime object though already it was
        )
    except (KeyError, ValueError) as exc:
        # This means Google/Auth0 or your own auth service issued a token
        # that broke the promised structural schema contract.
        logger.error(
            "Decoded JWT payload failed schema compliance mapping: %s",
            exc,
            exc_info=True,
        )
        # exc_info get full trace, error not warning since its server side problem
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Malformed internal token structure",
        )


# depends is a class
# which make whenver this function is called, first call this function inside
# and inject the result value
# it automatically forwards the active HTTP request, cookies, and headers into inside func
# without you mapping them manually.


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer_scheme)],
    # HTTPAuthorizationCredentials have .credentials (jwt) .scheme (bearer)
) -> TokenPayload:
    """FastAPI dependency — extracts and validates the bearer token."""
    return _decode_token(credentials.credentials)


# annotted[x,y] -> arg: x=y but y is class, x is another type thats why used


# ---------------------------------------------------------------------------
# Authorization helpers (used as sub-dependencies or in retriever)
# ---------------------------------------------------------------------------
def require_scope(required: AccessScope):
    """Factory: returns a dependency that enforces a specific scope."""

    async def _check(
        user: Annotated[TokenPayload, Depends(get_current_user)],
    ) -> TokenPayload:
        if AccessScope.ADMIN in user.scopes or required in user.scopes:
            return user
        logger.warning(
            "Scope denied: user=%s required=%s has=%s",
            user.sub,
            required,
            user.scopes,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Scope '{required}' required",
        )

    return _check


def build_scope_filter(user: TokenPayload) -> dict[str, list[str]]:
    """Build a metadata filter dict the retriever uses to restrict results.

    Returns e.g. {"access_scope": ["legal", "compliance"]}
    so only chunks tagged with those scopes are returned.
    Admin users get no filter (access everything).
    """
    if AccessScope.ADMIN in user.scopes:
        return {}  # no restriction
    return {"access_scope": [s.value for s in user.scopes]}


"""
http protocl warps into header and body 

GET /v1/products?category=electronics&limit=10 HTTP/1.1
Host: api.yourdomain.com
Authorization: Bearer eyJhbGciOi...
Accept: application/json (what format i want)


POST /v1/products HTTP/1.1
Host: api.yourdomain.com
Content-Type: application/json  (in what format i am giving body)
Accept: application/json
Authorization: Bearer eyJhbGciOi...  
(_bearer_scheme extracts these into HTTPAuthorizationCredentials object)


{
  "name": "Wireless Mouse",
  "price": 4500,
  "in_stock": true
}


this body is seen by uvicorn server, extracts json, pydantic then maps to args of route func
args and json recieved must be in same format


"""
