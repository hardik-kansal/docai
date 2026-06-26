from __future__ import annotations


import logging
from .repository import UserRepository, UserRow
from ..schemas import AccessScope
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

logger = logging.getLogger(__name__)
ph = PasswordHasher()

_DEFAULT_SCOPES = (AccessScope.LEGAL,)  # new users get minimal access
# better to use tuple here, so that couldnt be modifed elsewhere by mistake
# comma makes it a tupple else its just a enum object with value legal
# iterator will move over individual characters


class AuthService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def register_user(self, username: str, password: str) -> UserRow:
        if await self._repo.exists(username):
            raise ValueError(f"Username '{username}' already taken")
            # always raise http exceptions in routes, user should not be concerned
            # with app domain errors

        password_hash = ph.hash(password)
        # argon2 handles the salt generation and encoding/decoding automatically

        return await self._repo.create(
            username=username,
            password_hash=password_hash,
            scopes=_DEFAULT_SCOPES,  # scopes is list, but type conversion possible
        )

    async def verify_credentials(self, username: str, password: str) -> UserRow:
        user = await self._repo.get_by_username(username)
        if user is None:
            raise ValueError(f"Username '{username}' is None")
        try:
            # verify() returns True if it matches, or raises an exception if it doesn't
            ph.verify(user.password_hash, password)
        except VerifyMismatchError:
            raise ValueError("password does not match")
        return user
