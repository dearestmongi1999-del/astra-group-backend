from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.user import UserPublic
from app.utils.security import normalize_email


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

    @field_validator("email")
    @classmethod
    def clean_email(cls, value: EmailStr) -> str:
        return normalize_email(str(value))


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class AuthResponse(BaseModel):
    success: bool = True
    message: str
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: UserPublic


class MessageResponse(BaseModel):
    success: bool = True
    message: str
