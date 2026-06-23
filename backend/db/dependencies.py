from __future__ import annotations

import asyncpg
import logging

logger = logging.getLogger(__name__)


_pool: asyncpg.Pool | None = None


def set_asyncpg_pool(pool: asyncpg.Pool):
    global _pool
    _pool = pool


def get_asyncpg_pool() -> asyncpg.Pool:
    global _pool
    assert _pool is not None, "Postgres pool not initialized"
    return _pool
