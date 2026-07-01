from __future__ import annotations

import uuid
import logging
from dataclasses import dataclass
from datetime import datetime
import asyncpg

from ..models.schemas import AccessScope

logger = logging.getLogger(__name__)


# class.newattribute fails bz of slots-> no dict created
# class.attr=something fails since frozen
# dataclass sets __init__, repr which is print, eq (equal)
@dataclass(frozen=True, slots=True)
class UserRow:
    user_id: str
    username: str
    password_hash: str
    scopes: list[AccessScope]
    plan_type: str
    storage_used_bytes: int  # python is dyamic,
    # can handle int of any size at runtime, by using more ram
    created_at: datetime


class UserRepository:
    """All user-related SQL. Stateless — receives pool, no side effects."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def get_by_username(self, username: str) -> UserRow | None:
        row = await self._pool.fetchrow(
            """
            SELECT user_id, username, password_hash, scopes, plan_type, storage_used_bytes, created_at
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
            plan_type=row["plan_type"],
            storage_used_bytes=row["storage_used_bytes"],
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
            RETURNING user_id, username, password_hash, scopes, plan_type, storage_used_bytes, created_at
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
            plan_type=row["plan_type"],
            storage_used_bytes=row["storage_used_bytes"],
            created_at=row["created_at"],
        )

    async def exists(self, username: str) -> bool:
        val = await self._pool.fetchval(
            "SELECT EXISTS(SELECT 1 FROM users WHERE username = $1)",
            username,
        )

        return val
        # fetchval with exits returns true/false
        # if user first column value exists which is user_id

    async def get_by_user_id(self, user_id: int) -> UserRow | None:
        row = await self._pool.fetchrow(
            """
            SELECT user_id, username, password_hash, scopes, plan_type, storage_used_bytes, created_at
            FROM users
            WHERE user_id = $1
            """,
            user_id,
        )
        # asyncpg uses $1, $2... positional params (not %s).
        # This is a true prepared statement — immune to SQL injection.
        # Never use f-strings or .format() for query parameters.
        if row is None:
            return None
        return UserRow(
            user_id=row["user_id"].hex,  # afdf-afd-fafsds hex removes hyphen
            username=row["username"],
            password_hash=row["password_hash"],
            scopes=[AccessScope(s) for s in row["scopes"]],
            plan_type=row["plan_type"],
            storage_used_bytes=row["storage_used_bytes"],
            created_at=row["created_at"],
        )

    async def update_storage(self, user_id: uuid.UUID, filesize: int) -> UserRow | None:
        row = await self._pool.fetchrow(
            """
            UPDATE users
            SET storage_used_bytes = storage_used_bytes + $2
            WHERE user_id = $1
            RETURNING user_id, username, password_hash, scopes, plan_type, storage_used_bytes, created_at
            """,
            user_id,
            filesize,
        )
        if row is None:
            return None
        return UserRow(
            user_id=row["user_id"].hex,
            username=row["username"],
            password_hash=row["password_hash"],
            scopes=[AccessScope(s) for s in row["scopes"]],
            plan_type=row["plan_type"],
            storage_used_bytes=row["storage_used_bytes"],
            created_at=row["created_at"],
        )
