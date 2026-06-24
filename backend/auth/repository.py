from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
import asyncpg

from ..schemas import AccessScope

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class UserRow:
    """Domain object — what the DB returns. Not a Pydantic model.

    Pydantic is for API boundaries (serialization, validation).
    Internal domain objects use dataclasses — lighter, no JSON overhead.
    """

    user_id: str
    username: str
    password_hash: str
    scopes: list[AccessScope]
    created_at: datetime


class UserRepository:
    """All user-related SQL. Stateless — receives pool, no side effects."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_by_username(self, username: str) -> UserRow | None:
        row = await self._pool.fetchrow(
            """
            SELECT user_id, username, password_hash, scopes, created_at
            FROM users
            WHERE username = $1
            """,
            username,
        )
        # asyncpg uses $1, $2... positional params (not %s).
        # This is a true prepared statement — immune to SQL injection.
        # Never use f-strings or .format() for query parameters.
        if row is None:
            return None
        return UserRow(
            user_id=row["user_id"].hex,
            username=row["username"],
            password_hash=row["password_hash"],
            scopes=[AccessScope(s) for s in row["scopes"]],
            created_at=row["created_at"],
        )

    async def create(
        self,
        username: str,
        password_hash: str,
        scopes: list[AccessScope],
    ) -> UserRow:
        row = await self._pool.fetchrow(
            """
            INSERT INTO users (username, password_hash, scopes)
            VALUES ($1, $2, $3)
            RETURNING user_id, username, password_hash, scopes, created_at
            """,
            username,
            password_hash,
            [s.value for s in scopes],
        )
        # RETURNING avoids a second SELECT — one round trip for insert + fetch.
        # asyncpg maps Postgres array columns to Python lists automatically.
        return UserRow(
            user_id=row["user_id"].hex,
            username=row["username"],
            password_hash=row["password_hash"],
            scopes=[AccessScope(s) for s in row["scopes"]],
            created_at=row["created_at"],
        )

    async def exists(self, username: str) -> bool:
        val = await self._pool.fetchval(
            "SELECT EXISTS(SELECT 1 FROM users WHERE username = $1)",
            username,
        )
        # fetchval returns the first column of the first row — a single scalar.
        # EXISTS returns a boolean, so val is True/False directly.
        return val
