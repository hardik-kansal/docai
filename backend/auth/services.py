from __future__ import annotations
import uuid

import logging
from .repository import UserRepository, UserRow
from ..models.schemas import AccessScope
from ..config import settings
from google.oauth2 import id_token
import google.auth.transport.requests
import requests
import urllib.parse

logger = logging.getLogger(__name__)

_DEFAULT_SCOPES = (AccessScope.LEGAL,)  # new users get minimal access
# better to use tuple here, so that couldnt be modifed elsewhere by mistake
# comma makes it a tupple else its just a enum object with value legal
# iterator will move over individual characters


class AuthService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    def get_google_auth_url(self) -> str:
        params = {
            "client_id": settings().GOOGLE_CLIENT_ID,
            "redirect_uri": settings().GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "prompt": "consent",
        }
        return "https://accounts.google.com/o/oauth2/auth?" + urllib.parse.urlencode(
            params
        )

    async def handle_google_callback(self, code: str) -> UserRow:
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": settings().GOOGLE_CLIENT_ID,
            "client_secret": settings().GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings().GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }

        response = requests.post(token_url, data=data)
        if not response.ok:
            raise ValueError(f"Failed to fetch token from Google: {response.text}")

        tokens = response.json()
        id_token_jwt = tokens.get("id_token")

        if not id_token_jwt:
            raise ValueError("No id_token received from Google")

        request = google.auth.transport.requests.Request()
        id_info = id_token.verify_oauth2_token(
            id_token_jwt, request, settings().GOOGLE_CLIENT_ID
        )

        google_sub = id_info.get("sub")
        email = id_info.get("email")
        username = id_info.get("name") or email.split("@")[0]

        if not google_sub or not email:
            raise ValueError("Incomplete profile returned from Google")

        user = await self._repo.get_by_google_sub(google_sub)

        if user:
            # Update profile info on each login
            updated = await self._repo.update_profile(
                uuid.UUID(user.user_id), username=username, email=email
            )
            if not updated:
                raise ValueError("Failed to update user profile")
            return updated

        # Create new user
        new_user = await self._repo.create(
            username=username,
            email=email,
            google_sub=google_sub,
            scopes=_DEFAULT_SCOPES,
        )
        return new_user

    async def update_storage(self, user_id: str, filesize: int) -> UserRow | None:
        uid = uuid.UUID(user_id)
        user = await self._repo.update_storage(uid, filesize)
        if user is None:
            raise ValueError("user_id might not exist, unexplained error")
        return user

    async def get_by_user_id(self, user_id: str) -> UserRow | None:
        uid = uuid.UUID(user_id)
        user = await self._repo.get_by_user_id(uid)
        if user is None:
            raise ValueError("user_id does not exist")
        return user
