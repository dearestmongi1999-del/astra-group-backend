from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import timedelta
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import AuthResponse, MessageResponse, TokenResponse
from app.schemas.user import UserCreate, UserPublic
from app.services.auth_service import (
    authenticate_user,
    create_oauth_user,
    create_user,
    get_user_by_email,
    update_last_login,
)
from app.utils.dependencies import get_current_active_user
from app.utils.security import create_access_token


router = APIRouter(prefix="/auth", tags=["Authentication"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
OAUTH_STATE_MAX_AGE_SECONDS = 10 * 60


def _get_setting(name: str, default: str = "") -> str:
    value = getattr(settings, name, None)
    if value is None or value == "":
        value = os.getenv(name, default)
    return str(value or default).strip()


def _frontend_url() -> str:
    value = _get_setting("FRONTEND_URL", "http://localhost:3000")
    return value.rstrip("/")


def _google_client_id() -> str:
    return _get_setting("GOOGLE_CLIENT_ID")


def _google_client_secret() -> str:
    return _get_setting("GOOGLE_CLIENT_SECRET")


def _google_redirect_uri() -> str:
    return _get_setting(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/v1/auth/google/callback",
    )


def _oauth_state_secret() -> str:
    candidates = [
        getattr(settings, "SECRET_KEY", None),
        getattr(settings, "JWT_SECRET_KEY", None),
        getattr(settings, "JWT_SECRET", None),
        os.getenv("SECRET_KEY"),
        os.getenv("JWT_SECRET_KEY"),
        os.getenv("JWT_SECRET"),
        os.getenv("GOOGLE_CLIENT_SECRET"),
    ]
    for value in candidates:
        if value:
            return str(value)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="OAuth state secret is not configured.",
    )


def _base64_url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _base64_url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("utf-8"))


def _safe_frontend_path(value: str | None, fallback: str = "/dashboard") -> str:
    if not value or not isinstance(value, str):
        return fallback
    cleaned = value.strip()
    if not cleaned.startswith("/") or cleaned.startswith("//"):
        return fallback
    return cleaned


def _create_oauth_state(return_url: str | None = None) -> str:
    payload = {
        "iat": int(time.time()),
        "nonce": secrets.token_urlsafe(18),
        "returnUrl": _safe_frontend_path(return_url),
    }
    encoded_payload = _base64_url_encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    signature = hmac.new(
        _oauth_state_secret().encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{encoded_payload}.{signature}"


def _read_oauth_state(state: str | None) -> dict[str, Any]:
    if not state or "." not in state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state.",
        )

    encoded_payload, received_signature = state.rsplit(".", 1)
    expected_signature = hmac.new(
        _oauth_state_secret().encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(received_signature, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state signature.",
        )

    try:
        payload = json.loads(_base64_url_decode(encoded_payload).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth state payload.",
        ) from exc

    issued_at = int(payload.get("iat") or 0)
    if not issued_at or int(time.time()) - issued_at > OAUTH_STATE_MAX_AGE_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth state has expired. Please try again.",
        )

    payload["returnUrl"] = _safe_frontend_path(payload.get("returnUrl"))
    return payload


def _oauth_error_redirect(message: str) -> RedirectResponse:
    query = urlencode({"oauth_error": message})
    return RedirectResponse(url=f"{_frontend_url()}/auth/login?{query}")


def _make_access_token_for_user(user: User) -> str:
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_access_token(
        subject=str(user.id),
        expires_delta=expires_delta,
        extra_claims={
            "email": user.email,
            "role": user.role,
        },
    )


def _oauth_success_redirect(user: User, access_token: str, return_url: str | None = None) -> RedirectResponse:
    target_path = _safe_frontend_path(return_url)
    fragment = urlencode(
        {
            "oauth_success": "1",
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in_minutes": str(settings.ACCESS_TOKEN_EXPIRE_MINUTES),
            "returnUrl": target_path,
            "user_id": str(user.id),
            "full_name": user.full_name or "Astra User",
            "email": user.email,
            "role": user.role,
        }
    )
    return RedirectResponse(url=f"{_frontend_url()}/auth/login#{fragment}")


def build_auth_response(user: User, message: str) -> AuthResponse:
    access_token = _make_access_token_for_user(user)

    return AuthResponse(
        success=True,
        message=message,
        access_token=access_token,
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        user=UserPublic.model_validate(user),
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
) -> AuthResponse:
    user = create_user(db, payload)
    return build_auth_response(user, "Registration successful.")


@router.post("/login", response_model=AuthResponse)
def login_user(
    payload: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> AuthResponse:
    """
    Swagger-friendly login endpoint.

    Uses form fields:
        username: email address
        password: password
    """
    user = authenticate_user(db, payload.username, payload.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user account is inactive.",
        )

    user = update_last_login(db, user)
    return build_auth_response(user, "Login successful.")


@router.post("/login/form", response_model=TokenResponse)
def login_for_swagger_authorize(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Standard OAuth2 password flow endpoint for Swagger Authorize button.
    """
    user = authenticate_user(db, form_data.username, form_data.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user account is inactive.",
        )

    user = update_last_login(db, user)

    access_token = create_access_token(
        subject=str(user.id),
        extra_claims={
            "email": user.email,
            "role": user.role,
        },
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )


@router.get("/google/login")
def google_login(
    return_url: str | None = Query(default=None, alias="returnUrl"),
) -> RedirectResponse:
    """
    Starts Google OAuth login.

    Frontend button should redirect the browser to:
        /api/v1/auth/google/login
    """
    client_id = _google_client_id()
    redirect_uri = _google_redirect_uri()

    if not client_id or not _google_client_secret():
        return _oauth_error_redirect("Google login is not configured yet.")

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": _create_oauth_state(return_url),
        "prompt": "select_account",
        "access_type": "online",
        "include_granted_scopes": "true",
    }

    return RedirectResponse(url=f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
def google_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    """
    Google redirects here after the user approves login.

    This route exchanges the Google code for profile data, finds or creates an
    Astra user, creates the normal Astra JWT, then redirects back to the frontend
    login page with the token in the URL hash. The frontend stores the token and
    opens the correct dashboard.
    """
    if error:
        return _oauth_error_redirect(f"Google login cancelled or failed: {error}")

    if not code:
        return _oauth_error_redirect("Google did not return an authorization code.")

    try:
        state_payload = _read_oauth_state(state)
    except HTTPException as exc:
        return _oauth_error_redirect(str(exc.detail))

    client_id = _google_client_id()
    client_secret = _google_client_secret()
    redirect_uri = _google_redirect_uri()

    if not client_id or not client_secret:
        return _oauth_error_redirect("Google login is not configured yet.")

    try:
        with httpx.Client(timeout=15.0) as client:
            token_response = client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if token_response.status_code >= 400:
                return _oauth_error_redirect("Google token exchange failed.")

            token_payload = token_response.json()
            google_access_token = token_payload.get("access_token")
            if not google_access_token:
                return _oauth_error_redirect("Google did not return an access token.")

            profile_response = client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {google_access_token}"},
            )

            if profile_response.status_code >= 400:
                return _oauth_error_redirect("Could not read your Google profile.")

            profile = profile_response.json()
    except httpx.HTTPError:
        return _oauth_error_redirect("Could not connect to Google. Please try again.")

    email = str(profile.get("email") or "").strip().lower()
    full_name = str(profile.get("name") or "").strip()
    email_verified = bool(profile.get("email_verified", False))

    if not email:
        return _oauth_error_redirect("Google did not return an email address.")

    if not email_verified:
        return _oauth_error_redirect("Your Google email is not verified.")

    user = get_user_by_email(db, email)
    if user is None:
        user = create_oauth_user(
            db,
            email=email,
            full_name=full_name or email.split("@")[0],
        )

    if not user.is_active:
        return _oauth_error_redirect("This Astra account is inactive.")

    user = update_last_login(db, user)
    access_token = _make_access_token_for_user(user)

    return _oauth_success_redirect(
        user=user,
        access_token=access_token,
        return_url=state_payload.get("returnUrl"),
    )


@router.get("/me", response_model=UserPublic)
def get_my_profile(
    current_user: User = Depends(get_current_active_user),
) -> UserPublic:
    return UserPublic.model_validate(current_user)


@router.post("/logout", response_model=MessageResponse)
def logout_user() -> MessageResponse:
    """
    JWT logout is handled client-side by deleting the token.
    """
    return MessageResponse(
        success=True,
        message="Logout successful. Remove the token from the client application.",
    )
