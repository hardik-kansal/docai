from __future__ import annotations
# python when loading, checks from top to bottom and panics if class if defined later but
# its type hint used earlier, so earlier dev put "type" like in string format
# python does not check this now, which saves time to boot up
# instead of doing this, just put from __future__ import annotations in every req file
# only for type hint, if class is init then wrong error

from ..config import settings
import logging
from datetime import datetime, timedelta, timezone
from ..models.schemas import AccessScope
import uuid
from .cookies import ACCESS_COOKIE, REFRESH_COOKIE
import jwt
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

JWT_ALGORITHM = settings().JWT_ALGORITHM
JWT_SECRET = settings().JWT_SECRET
ISSUER = settings().ISSUER


class TokenPayload(BaseModel):
    sub: str = Field(default=..., description="user_id")  # ...means req field
    # field enforces extra condition
    scopes: list[AccessScope] = Field(
        description="Document scopes the user may retrieve",
    )
    exp: datetime
    iss: str
    jti: str = Field(default=...)
    type: str = Field(default=...)


def _decode_token(raw_token: str, expected_type: str) -> TokenPayload:
    try:
        data = jwt.decode(
            raw_token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],  # very imp, if not provide attacks possible
            issuer=ISSUER,
        )
    except jwt.ExpiredSignatureError:
        raise
    except Exception:
        logger.error("Token decoding failed: %s", exc_info=True)
        raise

    if data["type"] != expected_type:
        logger.error(
            "Token type mismatch: expected=%s got=%s", expected_type, data["type"]
        )
        raise ValueError("token type mismatched")  # custom error must be raised though

    return TokenPayload(
        sub=data["sub"],
        scopes=[AccessScope(s) for s in data.get("scopes", [])],
        # .get(value to search, default)
        # imp but not here some external auth providers when issue token
        # leaves those fields in payloads which are empty so there if
        # i write my another decoder without .get it would fail-> defensive engineering
        exp=datetime.fromtimestamp(data["exp"], tz=timezone.utc),
        jti=data["jti"],
        type=data["type"],
        iss=data["iss"],
        # converts to datetime object though already it was
    )


def _generate_jti() -> str:
    return uuid.uuid4().hex  # 32 hex chars, no dashes, URL-safe


def create_access_token(user_id: str, scopes: list[AccessScope]) -> tuple[str, str]:
    access_jti = _generate_jti()
    now = datetime.now(timezone.utc)
    access_payload = {
        "sub": user_id,
        "scopes": [s.value for s in scopes],
        "exp": now + timedelta(seconds=ACCESS_COOKIE.max_age),
        "iat": now,
        "iss": ISSUER,
        "jti": access_jti,
        "type": "access",  # prevents using refresh as access
    }
    access_jwt = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return access_jwt, access_jti


def create_refresh_token(user_id: str, scopes: list[AccessScope]) -> tuple[str, str]:
    refresh_jti = _generate_jti()
    now = datetime.now(timezone.utc)

    # datetime.now() uses local time
    # also jwt compares with server utc time

    refresh_payload = {
        "sub": user_id,
        "scopes": [s.value for s in scopes],
        "exp": now + timedelta(seconds=REFRESH_COOKIE.max_age),
        "iat": now,
        "iss": ISSUER,
        "jti": refresh_jti,
        "type": "refresh",
    }
    # jwt library when decode, looks for certain names predrefined like
    # sub,exp,iat,iss(issuer) changing these we lose native automation features
    # like exp check, hash check
    refresh_jwt = jwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return refresh_jwt, refresh_jti


def create_token_pair(
    user_id: str,
    scopes: list[AccessScope],
) -> tuple[str, str, str, str]:
    """
    Returns (access_jwt, access_jti, refresh_jwt,refresh_jti).
    """
    return (
        *create_access_token(user_id, scopes),
        *create_refresh_token(user_id, scopes),
    )


# unwraping needs outer brackets always
