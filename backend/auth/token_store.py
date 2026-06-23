import logging
import json

# json.dumps python dict->string of jsons
# json.loads  string of jsons->python dict
from datetime import datetime, timezone
from typing import Any
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class TokenStore:
    """
    Redis-backed store for refresh token lifecycle and access token blocklist.

    Keys:
        refresh:{jti}    → JSON {sub, scopes, created_at}  TTL = refresh expiry
    """

    _REFRESH_PREFIX = "refresh"

    def __init__(self, redis_client: redis.Redis) -> None:
        self._r = redis_client

    # -- refresh tokens --
    async def store_refresh(
        self,
        jti: str,
        user_id: str,
        scopes: list[str],
        ttl_seconds: int,
    ) -> None:
        """Persist a newly minted refresh token."""

        payload = json.dumps(
            {
                "sub": user_id,
                "scopes": scopes,
                "created_at": datetime.now(timezone.utc).isoformat(),
                # isoformat converts in dateTtime.ms
            }
        )
        key = f"{self._REFRESH_PREFIX}:{jti}"
        await self._r.set(key, payload, ex=ttl_seconds)
        logger.debug(
            "Stored refresh token user_id=%s scopes=%s jti=%s ttl=%ds",
            user_id,
            scopes,
            jti,
            ttl_seconds,
        )

    # use debug for every print used in dev, info for production major milestones, like launching etc

    async def validate_refresh(self, jti: str) -> dict[str, Any] | None:
        """Return stored payload if refresh token exists, else None."""

        raw = await self._r.get(f"{self._REFRESH_PREFIX}:{jti}")
        if raw is None:
            return None
        return json.loads(raw)

    async def revoke_refresh(self, jti: str) -> bool:
        """Delete refresh token. Returns True if it existed."""
        deleted = await self._r.delete(f"{self._REFRESH_PREFIX}:{jti}")
        if deleted:
            logger.debug("Revoked refresh token jti=%s", jti)
        return bool(deleted)

    async def revoke_all_user_sessions(self, user_id: str) -> int:
        """
        Nuclear option: scan and delete ALL refresh tokens for a user.
        Use when theft is detected (replayed rotation).

        Note: SCAN is O(N) on keyspace — acceptable because this is a rare
        security-critical path, not a hot path.
        """
        count = 0
        async for key in self._r.scan_iter(
            match=f"{self._REFRESH_PREFIX}:*", count=100
        ):
            raw = await self._r.get(key)
            if raw and json.loads(raw).get("sub") == user_id:
                await self._r.delete(key)
                count += 1
        logger.warning("Nuked %d sessions for user=%s", count, user_id)
        return count
