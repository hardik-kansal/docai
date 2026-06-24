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
    Redis-backed store for refresh token lifecycle.

    Keys:
        refresh:{jti}    → JSON {sub, scopes, created_at}  TTL = refresh expiry
    """

    _REFRESH_PREFIX = "refresh"

    def __init__(self, redis_client: redis.Redis) -> None:
        self._r = redis_client

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
