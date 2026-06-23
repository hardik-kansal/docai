from fastapi import Response, Request, Depends
import redis.asyncio as redis
from .token_store import TokenStore
from typing import Annotated
from . import tokens
from . import cookies
from jwt import ExpiredSignatureError

_redis_pool: redis.Redis | None = None


# @lru_cache(maxsize=1)
def get_token_store() -> TokenStore:
    assert _redis_pool is not None, "Redis not initialized"
    return TokenStore(_redis_pool)


# though here Token store instance is created each time when this func is called
# but its quite cheap to do since no expensive network, io etc
# redis_pool is network call to init connection to reddis
# keep only those globally which are expensive and needs lifecycle management


def set_redis_pool(pool: redis.Redis) -> None:
    """Called by main.py lifespan to inject the pool."""
    global _redis_pool
    _redis_pool = pool
    # global works HERE because we're inside the module that owns _redis_pool


def get_redis_pool() -> redis.Redis:
    """For cleanup in main.py lifespan shutdown."""
    assert _redis_pool is not None
    return _redis_pool


async def get_current_user(
    request: Request,
    response: Response,
    token_store: Annotated[TokenStore, Depends(get_token_store)],
) -> tokens.TokenPayload | None:
    refresh_jwt = request.cookies.get(cookies.REFRESH_COOKIE.key, None)
    access_jwt = request.cookies.get(cookies.ACCESS_COOKIE.key, None)
    if access_jwt is None or refresh_jwt is None:
        return None

    try:
        access_payload = tokens._decode_token(access_jwt, expected_type="access")
        return access_payload
    except ExpiredSignatureError:
        try:
            refresh_payload = tokens._decode_token(refresh_jwt, expected_type="refresh")
            access_jwt_new, _ = tokens.create_access_token(
                refresh_payload.sub, refresh_payload.scopes
            )
            cookies.set_auth_cookies(response, access_jwt_new, refresh_jwt)
            return tokens._decode_token(access_jwt_new, expected_type="access")
        except ExpiredSignatureError:
            return None
