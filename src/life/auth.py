from fastapi import Request, HTTPException, Form
from fastapi.responses import RedirectResponse

from life.config import settings

SESSION_COOKIE_NAME = "life_session"


def verify_auth(request: Request) -> None:
    """Dependency to verify user is authenticated."""
    session = request.cookies.get(SESSION_COOKIE_NAME)
    if session != settings.secret_key:
        raise HTTPException(status_code=401, detail="Not authenticated")


def check_auth(request: Request) -> bool:
    """Check if user is authenticated without raising."""
    session = request.cookies.get(SESSION_COOKIE_NAME)
    return session == settings.secret_key


async def login(secret: str = Form(...)) -> RedirectResponse:
    """Verify secret and set session cookie."""
    if secret != settings.secret_key:
        raise HTTPException(status_code=401, detail="Invalid secret")

    response = RedirectResponse(url="/shipments", status_code=303)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        settings.secret_key,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=60 * 60 * 24 * 30,  # 30 days
    )
    return response


def logout() -> RedirectResponse:
    """Clear session cookie."""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response
