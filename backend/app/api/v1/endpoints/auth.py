"""
HospitalOps AI — Authentication Endpoints.

Provides login, refresh, logout, and current user info.
"""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr

from app.api.dependencies import get_auth_service, get_current_user
from app.core.config import get_settings
from app.core.security import get_permissions_for_role
from app.models.user import UserDocument, UserRead
from app.services.auth import AuthService, TokenResponse

router = APIRouter()
settings = get_settings()

# ── Schemas ───────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """
    Authenticate user and return an access token.
    Sets a secure HttpOnly cookie containing the refresh token.
    """
    user = await auth_service.authenticate_user(login_data.email, login_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tokens = await auth_service.create_tokens(user)

    # Set the refresh token in an HttpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/api/v1/auth",  # Restrict cookie to auth routes
    )

    return TokenResponse(access_token=tokens.access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> TokenResponse:
    """
    Issue a new access token and refresh token using the HttpOnly cookie.
    """
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
        )

    tokens = await auth_service.refresh_session(refresh_token)

    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh session",
        )

    # Set the new refresh token (rotation)
    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path="/api/v1/auth",
    )

    return TokenResponse(access_token=tokens.access_token)


@router.post("/logout")
async def logout(
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> dict[str, str]:
    """
    Revoke the current refresh session and clear the cookie.
    """
    if refresh_token:
        await auth_service.revoke_session(refresh_token)

    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
    )

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserRead)
async def read_users_me(
    current_user: Annotated[UserDocument, Depends(get_current_user)],
) -> UserRead:
    """
    Get the currently authenticated user's profile and resolved permissions.
    """
    # The Pydantic model_validate handles transforming the UserDocument into UserRead
    user_data = current_user.model_dump()

    # Inject resolved permissions for the frontend
    user_data["permissions"] = get_permissions_for_role(current_user.role)

    return UserRead(**user_data)
