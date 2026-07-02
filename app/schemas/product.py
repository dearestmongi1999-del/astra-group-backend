from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ProductImageTypeValue = Literal["primary", "banner", "gallery"]
ProductRequestStatusValue = Literal["new", "contacted", "quoted", "completed", "cancelled"]


class ProductImagePublic(BaseModel):
    id: int
    product_id: int
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


class ProductImageCreate(BaseModel):
    image_url: str
    image_path: str | None = None
    original_filename: str | None = None
    alt_text: str | None = None
    image_type: ProductImageTypeValue = "gallery"
    is_primary: bool = False
    is_banner: bool = False
    display_order: int = 0


class ProductImageUpdate(BaseModel):
    alt_text: str | None = None
    image_type: ProductImageTypeValue | None = None
    is_primary: bool | None = None
    is_banner: bool | None = None
    display_order: int | None = None


class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str | None = Field(default=None, max_length=280)
    category: str | None = Field(default=None, max_length=120)
    short_description: str | None = Field(default=None, max_length=500)
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="TZS", max_length=10)
    unit: str | None = Field(default=None, max_length=100)
    price_note: str | None = Field(default=None, max_length=255)
    stock_quantity: int | None = Field(default=None, ge=0)
    sku: str | None = Field(default=None, max_length=120)
    is_featured: bool = False
    is_active: bool = True
    display_order: int = 0
    meta_title: str | None = Field(default=None, max_length=255)
    meta_description: str | None = Field(default=None, max_length=500)

    @field_validator("name", "slug", "category", "short_description", "unit", "price_note", "sku", "currency", "meta_title", "meta_description")
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


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    slug: str | None = Field(default=None, max_length=280)
    category: str | None = Field(default=None, max_length=120)
    short_description: str | None = Field(default=None, max_length=500)
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, max_length=10)
    unit: str | None = Field(default=None, max_length=100)
    price_note: str | None = Field(default=None, max_length=255)
    stock_quantity: int | None = Field(default=None, ge=0)
    sku: str | None = Field(default=None, max_length=120)
    is_featured: bool | None = None
    is_active: bool | None = None
    display_order: int | None = None
    meta_title: str | None = Field(default=None, max_length=255)
    meta_description: str | None = Field(default=None, max_length=500)

    @field_validator("name", "slug", "category", "short_description", "unit", "price_note", "sku", "currency", "meta_title", "meta_description")
    @classmethod
    def clean_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ProductPublic(BaseModel):
    id: int
    created_by_user_id: int | None = None
    name: str
    slug: str
    category: str | None = None
    short_description: str | None = None
    description: str | None = None
    price: Decimal | None = None
    currency: str
    unit: str | None = None
    price_note: str | None = None
    stock_quantity: int | None = None
    sku: str | None = None
    is_featured: bool
    is_active: bool
    display_order: int
    meta_title: str | None = None
    meta_description: str | None = None
    images: list[ProductImagePublic] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    success: bool = True
    total: int
    items: list[ProductPublic]


class ProductRequestCreate(BaseModel):
    product_id: int | None = None
    full_name: str = Field(..., min_length=2, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=100)
    company_name: str | None = Field(default=None, max_length=255)
    product_name: str = Field(..., min_length=2, max_length=255)
    quantity: str | None = Field(default=None, max_length=100)
    destination: str | None = Field(default=None, max_length=255)
    delivery_required: bool = False
    message: str | None = None
    source: str = Field(default="website", max_length=100)

    @field_validator("full_name", "email", "phone", "company_name", "product_name", "quantity", "destination", "source")
    @classmethod
    def clean_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def require_contact(self) -> "ProductRequestCreate":
        if not self.email and not self.phone:
            raise ValueError("Provide at least one contact method: email or phone.")
        return self


class ProductRequestStatusUpdate(BaseModel):
    status: ProductRequestStatusValue
    admin_notes: str | None = None


class ProductRequestPublic(BaseModel):
    id: int
    user_id: int | None = None
    product_id: int | None = None
    full_name: str
    email: str | None = None
    phone: str | None = None
    company_name: str | None = None
    product_name: str
    quantity: str | None = None
    destination: str | None = None
    delivery_required: bool
    message: str | None = None
    status: str
    admin_notes: str | None = None
    source: str
    whatsapp_link: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductRequestListResponse(BaseModel):
    success: bool = True
    total: int
    items: list[ProductRequestPublic]
