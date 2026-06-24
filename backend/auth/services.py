from __future__ import annotations


import logging
import bcrypt
from .repository import UserRepository, UserRow
from ..schemas import AccessScope

logger = logging.getLogger(__name__)


_DEFAULT_SCOPES = [AccessScope.LEGAL]  # new users get minimal access


# bcrypt is intentionally CPU-heavy (— slows brute force).
# In production with high signup volume, offload to a thread via
# asyncio.to_thread(bcrypt.hashpw, ...) to avoid blocking the event loop.
# For your scale, sync is fine.


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


# encode converts to bytes, since lib expects it
# decode coneverts bytes to str


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# bcrypt.checkpw() extracts the salt from the stored hash


class AuthService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def register_user(self, username: str, password: str) -> UserRow:
        if await self._repo.exists(username):
            raise ValueError(f"Username '{username}' already taken")
            # always raise http exceptions in routes, user should not be concerned
            # with app domain errors

        password_hash = _hash_password(password)

        return await self._repo.create(
            username=username,
            password_hash=password_hash,
            scopes=_DEFAULT_SCOPES,
        )

    async def verify_credentials(self, username: str, password: str) -> UserRow:
        user = await self._repo.get_by_username(username)
        if user is None or not _verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")
            # dont use "user not found" and "wrong password"
            # to prevent username enumeration attacks.
            # means attacker knows which username exists
        return user
