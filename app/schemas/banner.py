from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


BannerTypeValue = Literal["home", "service", "product", "promotion", "about"]
BannerTargetTypeValue = Literal["none", "service", "product", "custom"]


class FrontendBannerBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    subtitle: str | None = Field(default=None, max_length=500)
    description: str | None = None
    button_text: str | None = Field(default=None, max_length=120)
    button_link: str | None = Field(default=None, max_length=1000)
    image_url: str | None = Field(default=None, max_length=1000)
    alt_text: str | None = Field(default=None, max_length=255)
    banner_type: BannerTypeValue = "home"
    target_type: BannerTargetTypeValue = "none"
    target_id: int | None = None
    display_order: int = 0
    is_active: bool = True
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @field_validator("title", "subtitle", "button_text", "button_link", "image_url", "alt_text")
    @classmethod
    def clean_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def validate_dates(self) -> "FrontendBannerBase":
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be later than starts_at.")
        return self


class FrontendBannerCreate(FrontendBannerBase):
    pass


class FrontendBannerUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    subtitle: str | None = Field(default=None, max_length=500)
    description: str | None = None
    button_text: str | None = Field(default=None, max_length=120)
    button_link: str | None = Field(default=None, max_length=1000)
    image_url: str | None = Field(default=None, max_length=1000)
    alt_text: str | None = Field(default=None, max_length=255)
    banner_type: BannerTypeValue | None = None
    target_type: BannerTargetTypeValue | None = None
    target_id: int | None = None
    display_order: int | None = None
    is_active: bool | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None

    @field_validator("title", "subtitle", "button_text", "button_link", "image_url", "alt_text")
    @classmethod
    def clean_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class FrontendBannerPublic(BaseModel):
    id: int
    created_by_user_id: int | None = None
    title: str
    subtitle: str | None = None
    description: str | None = None
    button_text: str | None = None
    button_link: str | None = None
    image_url: str | None = None
    image_path: str | None = None
    original_filename: str | None = None
    alt_text: str | None = None
    banner_type: str
    target_type: str
    target_id: int | None = None
    display_order: int
    is_active: bool
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FrontendBannerListResponse(BaseModel):
    success: bool = True
    total: int
    items: list[FrontendBannerPublic]
