from .dependencies import get_token_store
from .token_store import TokenStore
from .cookies import REFRESH_COOKIE, set_auth_cookies, clear_auth_cookies
from . import tokens

from fastapi import HTTPException, APIRouter, Response, Request, Depends
from pydantic import BaseModel, Field
from .services import AuthService
from ..db.dependencies import get_auth_service
import logging
from typing import Annotated

logger = logging.getLogger(__name__)


class LoginRequest(BaseModel):
    username: str = Field(default=..., max_length=10, min_length=1)
    pwd: str = Field(default=..., max_length=10, min_length=5)


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/signup")
async def signup(
    credentials: LoginRequest,
    authService: Annotated[AuthService, Depends(get_auth_service)],
):
    try:
        user = await authService.register_user(credentials.username, credentials.pwd)
    except ValueError as exc:
        # 409 is req is valid but interfer with current status of server
        raise HTTPException(status_code=409, detail=str(exc))
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
        access_jwt, access_jti, refresh_jwt, refresh_jti = tokens.create_token_pair(
            user_id=user.user_id,
            scopes=user.scopes,
        )
        # Store refresh in Redis
        await token_store.store_refresh(
            jti=refresh_jti,
            user_id=user.user_id,
            scopes=[s.value for s in user.scopes],
            ttl_seconds=REFRESH_COOKIE.max_age,
        )
    except (
        ValueError
    ):  # catch only value error if something else wrong would never know
        raise HTTPException(status_code=401, detail="invalid credentials")
    # Set cookies
    set_auth_cookies(response, access_jwt, refresh_jwt)
    return {"message": "authenticated", "user_id": user.user_id}


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    token_store: Annotated[TokenStore, Depends(get_token_store)],
):
    raw_refresh = request.cookies.get(REFRESH_COOKIE.key)
    if raw_refresh is None:
        raise HTTPException(status_code=401, detail="No refresh token")

    # Decode (validates exp, iss, signature)
    old_payload = tokens._decode_token(raw_refresh, expected_type="refresh")

    # Server-side validation — is this jti still live in Redis?
    stored = await token_store.validate_refresh(old_payload.jti)
    if stored is None:
        # Possible theft: token was already rotated by the real user.
        # Nuclear response: kill ALL sessions for this user.
        logger.critical(
            "Refresh token replay detected! jti=%s user=%s",
            old_payload.jti,
            old_payload.sub,
        )
        await token_store.revoke_all_user_sessions(old_payload.sub)
        clear_auth_cookies(response)
        raise HTTPException(status_code=401, detail="Session invalidated")

    # Rotate: kill old, mint new
    await token_store.revoke_refresh(old_payload.jti)

    access_jwt, access_jti, refresh_jwt, refresh_jti = tokens.create_token_pair(
        user_id=old_payload.sub,
        scopes=old_payload.scopes,
    )
    await token_store.store_refresh(
        jti=refresh_jti,
        user_id=old_payload.sub,
        scopes=[s.value for s in old_payload.scopes],
        ttl_seconds=REFRESH_COOKIE.max_age,
    )
    set_auth_cookies(response, access_jwt, refresh_jwt)

    return {"message": "tokens rotated"}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    token_store: Annotated[TokenStore, Depends(get_token_store)],
):
    # Kill refresh
    refresh_jwt = request.cookies.get(REFRESH_COOKIE.key, None)
    if refresh_jwt is not None:
        payload = tokens._decode_token(refresh_jwt, expected_type="refresh")
        await token_store.revoke_refresh(payload.jti)

    clear_auth_cookies(response)
    return {"message": "logged out"}
