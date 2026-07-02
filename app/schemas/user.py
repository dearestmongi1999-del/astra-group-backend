from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.utils.security import is_password_strong_enough, normalize_email


UserRoleValue = Literal["admin", "staff", "customer"]


class UserBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=100)

    @field_validator("email")
    @classmethod
    def clean_email(cls, value: EmailStr) -> str:
        return normalize_email(str(value))

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Full name must contain at least 2 characters.")
        return value

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        if not is_password_strong_enough(value):
            raise ValueError(
                "Password must be at least 8 characters and include both letters and numbers."
            )
        return value


class UserCreateAdmin(UserCreate):
    role: UserRoleValue = "customer"
    is_active: bool = True
    is_verified: bool = False


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, max_length=100)

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Full name must contain at least 2 characters.")
        return value

    @field_validator("phone")
    @classmethod
    def clean_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class UserAdminUpdate(UserUpdate):
    role: UserRoleValue | None = None
    is_active: bool | None = None
    is_verified: bool | None = None


class UserStatusUpdate(BaseModel):
    is_active: bool | None = None
    is_verified: bool | None = None
    role: UserRoleValue | None = None


class UserPublic(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone: str | None = None
    role: str
    is_active: bool
    is_verified: bool
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    success: bool = True
    total: int
    items: list[UserPublic]
