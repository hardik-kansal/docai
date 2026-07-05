from dataclasses import dataclass
from fastapi import Response
from ..config import settings


@dataclass(frozen=True, slots=True)
# frozen means classObject.attribute=change does not works
# className.new_attribute works previously even if not in class defination but not with
# slots = True means no __dict__ created for each object, uses class __dict__
class CookieConfig:
    """Immutable cookie configuration. One instance per cookie type."""

    key: str
    max_age: int  # seconds
    path: str
    httponly: bool = True
    secure: bool = True if settings().is_prod else False
    # since works on localhost for localdev
    samesite: str = "lax"


ACCESS_COOKIE = CookieConfig(
    key="access_token",
    max_age=15 * 60,  # 15 minutes
    path="/",
    samesite="lax",
)
REFRESH_COOKIE = CookieConfig(
    key="refresh_token",
    max_age=60 * 60 * 24 * 7,
    path="/",
    samesite="strict",
)


def set_access_cookie(
    response: Response,
    access_jwt: str,
) -> None:
    """Set access cookies on a FastAPI Response."""

    response.set_cookie(
        key=ACCESS_COOKIE.key,
        value=access_jwt,
        max_age=ACCESS_COOKIE.max_age,
        path=ACCESS_COOKIE.path,
        httponly=ACCESS_COOKIE.httponly,
        secure=ACCESS_COOKIE.secure,
        samesite=ACCESS_COOKIE.samesite,
    )


def set_auth_cookies(
    response: Response,
    access_jwt: str,
    refresh_jwt: str,
) -> None:
    """Set both auth cookies on a FastAPI Response."""
    for cookie_cfg, token in [
        (ACCESS_COOKIE, access_jwt),
        (REFRESH_COOKIE, refresh_jwt),
    ]:
        response.set_cookie(
            key=cookie_cfg.key,
            value=token,
            max_age=cookie_cfg.max_age,
            path=cookie_cfg.path,
            httponly=cookie_cfg.httponly,
            secure=cookie_cfg.secure,
            samesite=cookie_cfg.samesite,
        )


def clear_auth_cookies(response: Response) -> None:
    """Expire both auth cookies immediately."""
    for cookie_cfg in (ACCESS_COOKIE, REFRESH_COOKIE):
        response.delete_cookie(
            key=cookie_cfg.key,
            path=cookie_cfg.path,  # browser needs both
        )
