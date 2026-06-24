from __future__ import annotations
from ..auth.repository import UserRepository
from ..auth.services import AuthService
import asyncpg
import logging

logger = logging.getLogger(__name__)


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
