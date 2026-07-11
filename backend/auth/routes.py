from .dependencies import get_token_store
from .token_store import TokenStore
from .cookies import REFRESH_COOKIE, set_auth_cookies, clear_auth_cookies
from . import tokens

from fastapi import HTTPException, APIRouter, Response, Request, Depends
from pydantic import BaseModel, Field
from .services import AuthService
from .dependencies import get_auth_service, get_current_user, User

import logging
from typing import Annotated
from jwt import ExpiredSignatureError

logger = logging.getLogger(__name__)


class LoginRequest(BaseModel):
    username: str = Field(default=..., max_length=10, min_length=1)
    pwd: str = Field(default=..., max_length=10, min_length=1)


class UserProfileResponse(BaseModel):
    user_id: str
    username: str
    scopes: list[str]
    plan_type: str
    storage_used_bytes: int


router = APIRouter(prefix="/api/v1/auth")


@router.get("/me")
async def me(
    user: Annotated[User, Depends(get_current_user)],
    authService: Annotated[AuthService, Depends(get_auth_service)],
) -> UserProfileResponse:
    user_row = await authService.get_by_user_id(user.user_id)
    return UserProfileResponse(
        user_id=user_row.user_id,
        username=user_row.username,
        scopes=[s.value for s in user_row.scopes],
        plan_type=user_row.plan_type,
        storage_used_bytes=user_row.storage_used_bytes,
    )


@router.post("/signup")
async def signup(
    credentials: LoginRequest,
    authService: Annotated[AuthService, Depends(get_auth_service)],
):
    try:
        user = await authService.register_user(credentials.username, credentials.pwd)
    except ValueError:  # though here custom made error should be there
        raise HTTPException(status_code=409, detail="invalid credentials")
    return {"message": "signup success", "user_id": user.user_id}


# fastapi is coroutine object which is run when server is started
# so a even loop is created, when req came, endpoint func is just called with await
# also if func is not asyn def then runs in seperate thread to avoid blocking main loop
@router.post("/login")
async def login(
    credentials: LoginRequest,
    response: Response,  # this is injected like dependency by fastapi
    token_store: Annotated[TokenStore, Depends(get_token_store)],
    authService: Annotated[AuthService, Depends(get_auth_service)],
):
    try:
        user = await authService.verify_credentials(
            credentials.username, credentials.pwd
        )
    except ValueError:  # though here custom made error should be there
        raise HTTPException(status_code=401, detail="invalid credentials")

    access_jwt, access_jti, refresh_jwt, refresh_jti = tokens.create_token_pair(
        user_id=user.user_id,
        scopes=user.scopes,
    )

    await token_store.store_refresh(
        jti=refresh_jti,
        user_id=user.user_id,
        scopes=[s.value for s in user.scopes],
        ttl_seconds=REFRESH_COOKIE.max_age,
    )
    # this must be set at last ,in case refresh fails, this wont be set in response.
    set_auth_cookies(response, access_jwt, refresh_jwt)
    return {"message": "authenticated", "user_id": user.user_id}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    token_store: Annotated[TokenStore, Depends(get_token_store)],
):
    refresh_jwt = request.cookies.get(REFRESH_COOKIE.key, None)
    clear_auth_cookies(response)
    # must be done in starting else if error occurs might not cleaned up
    if refresh_jwt is not None:
        try:
            payload = tokens._decode_token(refresh_jwt, expected_type="refresh")
            await token_store.revoke_refresh(payload.jti)
        except ExpiredSignatureError:
            logger.warning("refresh token expired before logout")
        except Exception:
            raise HTTPException(status_code=400, detail="invalid cookie received")
    return {"message": "logged out"}
