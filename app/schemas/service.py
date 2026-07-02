from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ServiceTypeValue = Literal["cleaning", "fumigation"]
ServiceImageTypeValue = Literal["primary", "banner", "gallery"]
ServiceBookingStatusValue = Literal["new", "contacted", "confirmed", "completed", "cancelled"]


class ServiceImagePublic(BaseModel):
    id: int
    service_id: int
    image_url: str
    image_path: str | None = None
    original_filename: str | None = None
    alt_text: str | None = None
    image_type: str
    is_primary: bool
    is_banner: bool
    display_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ServiceImageCreate(BaseModel):
    image_url: str
    image_path: str | None = None
    original_filename: str | None = None
    alt_text: str | None = None
    image_type: ServiceImageTypeValue = "gallery"
    is_primary: bool = False
    is_banner: bool = False
    display_order: int = 0


class ServiceImageUpdate(BaseModel):
    alt_text: str | None = None
    image_type: ServiceImageTypeValue | None = None
    is_primary: bool | None = None
    is_banner: bool | None = None
    display_order: int | None = None


class ServiceBase(BaseModel):
    service_type: ServiceTypeValue = "cleaning"
    title: str = Field(..., min_length=2, max_length=255)
    slug: str | None = Field(default=None, max_length=280)
    short_description: str | None = Field(default=None, max_length=500)
    description: str | None = None
    starting_price: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="TZS", max_length=10)
    price_note: str | None = Field(default=None, max_length=255)
    duration: str | None = Field(default=None, max_length=120)
    is_featured: bool = False
    is_active: bool = True
    display_order: int = 0
    meta_title: str | None = Field(default=None, max_length=255)
    meta_description: str | None = Field(default=None, max_length=500)

    @field_validator("title", "slug", "short_description", "price_note", "duration", "currency", "meta_title", "meta_description")
    @classmethod
    def clean_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("currency")
    @classmethod
    def clean_currency(cls, value: str | None) -> str:
        if not value:
            return "TZS"
        return value.strip().upper()


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    service_type: ServiceTypeValue | None = None
    title: str | None = Field(default=None, min_length=2, max_length=255)
    slug: str | None = Field(default=None, max_length=280)
    short_description: str | None = Field(default=None, max_length=500)
    description: str | None = None
    starting_price: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=10)
    price_note: str | None = Field(default=None, max_length=255)
    duration: str | None = Field(default=None, max_length=120)
    is_featured: bool | None = None
    is_active: bool | None = None
    display_order: int | None = None
    meta_title: str | None = Field(default=None, max_length=255)
    meta_description: str | None = Field(default=None, max_length=500)

    @field_validator("title", "slug", "short_description", "price_note", "duration", "currency", "meta_title", "meta_description")
    @classmethod
    def clean_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ServicePublic(BaseModel):
    id: int
    created_by_user_id: int | None = None
    service_type: str
    title: str
    slug: str
    short_description: str | None = None
    description: str | None = None
    starting_price: Decimal | None = None
    currency: str
    price_note: str | None = None
    duration: str | None = None
    is_featured: bool
    is_active: bool
    display_order: int
    meta_title: str | None = None
    meta_description: str | None = None
    images: list[ServiceImagePublic] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ServiceListResponse(BaseModel):
    success: bool = True
    total: int
    items: list[ServicePublic]


class ServiceBookingCreate(BaseModel):
    service_id: int | None = None
    full_name: str = Field(..., min_length=2, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=100)
    company_name: str | None = Field(default=None, max_length=255)
    service_type: ServiceTypeValue = "cleaning"
    preferred_date: date | None = None
    preferred_time: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=120)
    message: str | None = None
    source: str = Field(default="website", max_length=100)

    @field_validator("full_name", "email", "phone", "company_name", "preferred_time", "address", "city", "source")
    @classmethod
    def clean_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def require_contact(self) -> "ServiceBookingCreate":
        if not self.email and not self.phone:
            raise ValueError("Provide at least one contact method: email or phone.")
        return self


class ServiceBookingStatusUpdate(BaseModel):
    status: ServiceBookingStatusValue
    admin_notes: str | None = None


class ServiceBookingPublic(BaseModel):
    id: int
    user_id: int | None = None
    service_id: int | None = None
    full_name: str
    email: str | None = None
    phone: str | None = None
    company_name: str | None = None
    service_type: str
    preferred_date: date | None = None
    preferred_time: str | None = None
    address: str | None = None
    city: str | None = None
    message: str | None = None
    status: str
    admin_notes: str | None = None
    source: str
    whatsapp_link: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ServiceBookingListResponse(BaseModel):
    success: bool = True
    total: int
    items: list[ServiceBookingPublic]
