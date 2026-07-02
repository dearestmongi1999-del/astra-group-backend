from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import AuthResponse, MessageResponse, TokenResponse
from app.schemas.user import UserCreate, UserPublic
from app.services.auth_service import authenticate_user, create_user, update_last_login
from app.utils.dependencies import get_current_active_user
from app.utils.security import create_access_token


router = APIRouter(prefix="/auth", tags=["Authentication"])


def build_auth_response(user: User, message: str) -> AuthResponse:
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=expires_delta,
        extra_claims={
            "email": user.email,
            "role": user.role,
        },
    )

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
