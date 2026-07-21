from .dependencies import get_token_store
from .token_store import TokenStore
from .cookies import REFRESH_COOKIE, set_auth_cookies, clear_auth_cookies
from . import tokens
from fastapi.responses import RedirectResponse
from fastapi import HTTPException, APIRouter, Response, Request, Depends
from pydantic import BaseModel
from .services import AuthService
from .dependencies import get_auth_service, get_current_user, User
from ..config import settings
import logging
from typing import Annotated
from jwt import ExpiredSignatureError

logger = logging.getLogger(__name__)


class UserProfileResponse(BaseModel):
    user_id: str
    username: str
    email: str
    scopes: list[str]
    plan_type: str
    storage_used_bytes: int
    created_at: str


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
        email=user_row.email,
        scopes=[s.value for s in user_row.scopes],
        plan_type=user_row.plan_type,
        storage_used_bytes=user_row.storage_used_bytes,
        created_at=user_row.created_at.isoformat(),
    )


@router.get("/login/google")
async def google_login(
    authService: Annotated[AuthService, Depends(get_auth_service)],
):
    url = authService.get_google_auth_url()
    return {"url": url}


@router.get("/login/google/callback")
async def google_callback(
    code: str,
    token_store: Annotated[TokenStore, Depends(get_token_store)],
    authService: Annotated[AuthService, Depends(get_auth_service)],
):
    try:
        user = await authService.handle_google_callback(code)
    except ValueError:
        raise HTTPException(status_code=400, detail="google auth failed")

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

    redirect_response = RedirectResponse(url=f"{settings().FRONTEND_URL}/dashboard")
    set_auth_cookies(redirect_response, access_jwt, refresh_jwt)
    return redirect_response


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
