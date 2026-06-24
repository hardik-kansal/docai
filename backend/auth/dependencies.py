from fastapi import Response, Request
import redis.asyncio as redis
from .token_store import TokenStore
from . import tokens
from . import cookies
from jwt import ExpiredSignatureError
from .repository import UserRepository
from .services import AuthService
import asyncpg
import logging

logger = logging.getLogger(__name__)


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
    # global only searches in current file


def get_redis_pool() -> redis.Redis:
    """For cleanup in main.py lifespan shutdown."""
    assert _redis_pool is not None
    return _redis_pool


_pool: asyncpg.Pool | None = None


def set_asyncpg_pool(pool: asyncpg.Pool):
    global _pool
    _pool = pool


def get_asyncpg_pool() -> asyncpg.Pool:
    # global _pool -> though in this file not req,
    # but global suggests _pool is being written
    assert _pool is not None, "Postgres pool not initialized"
    return _pool


def get_user_repository() -> UserRepository:
    return UserRepository(get_asyncpg_pool())


def get_auth_service() -> AuthService:
    return AuthService(get_user_repository())


async def get_current_user(
    request: Request,
    response: Response,
) -> tokens.TokenPayload | None:
    refresh_jwt = request.cookies.get(cookies.REFRESH_COOKIE.key, None)
    access_jwt = request.cookies.get(cookies.ACCESS_COOKIE.key, None)
    if access_jwt is None or refresh_jwt is None:
        return None

    try:
        access_payload = tokens._decode_token(access_jwt, expected_type="access")
    except ExpiredSignatureError:
        logger.warning("access token expired attempting refresh")
        try:
            refresh_payload = tokens._decode_token(refresh_jwt, expected_type="refresh")
        except ExpiredSignatureError:
            logger.warning("both access and refresh token expired")
            return None
        access_jwt_new, _ = tokens.create_access_token(
            refresh_payload.sub, refresh_payload.scopes
        )
        cookies.set_access_cookie(response, access_jwt_new)
        return tokens._decode_token(access_jwt_new, expected_type="access")
    return access_payload
