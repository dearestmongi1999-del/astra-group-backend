from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application settings.

    Values are loaded from the .env file in the backend root folder.
    """

    # ---------------------------------------------------------
    # App
    # ---------------------------------------------------------
    APP_NAME: str = "Astra Group API"
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # ---------------------------------------------------------
    # Database
    # ---------------------------------------------------------
    DATABASE_URL: str

    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # ---------------------------------------------------------
    # CORS
    # ---------------------------------------------------------
    ALLOWED_ORIGINS: str = Field(
        default=(
            "http://localhost:3000,"
            "http://127.0.0.1:3000,"
            "http://localhost:5173,"
            "http://127.0.0.1:5173"
        )
    )

    # ---------------------------------------------------------
    # JWT Authentication
    # ---------------------------------------------------------
    JWT_SECRET_KEY: str = "change_this_to_a_long_random_secret_key_for_astra_group"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # ---------------------------------------------------------
    # Admin notifications
    # ---------------------------------------------------------
    ADMIN_EMAIL: str | None = None
    ADMIN_PHONE: str | None = None

    # ---------------------------------------------------------
    # Email SMTP
    # ---------------------------------------------------------
    EMAIL_ENABLED: bool = False
    EMAIL_HOST: str | None = None
    EMAIL_PORT: int = 587
    EMAIL_USERNAME: str | None = None
    EMAIL_PASSWORD: str | None = None
    EMAIL_FROM: str | None = None
    EMAIL_FROM_NAME: str = "Astra Group"
    EMAIL_USE_TLS: bool = True
    EMAIL_TIMEOUT_SECONDS: int = 30

    # ---------------------------------------------------------
    # WhatsApp
    # ---------------------------------------------------------
    WHATSAPP_ENABLED: bool = True
    WHATSAPP_PROVIDER: str = "manual"
    WHATSAPP_BUSINESS_NUMBER: str | None = None

    # Future WhatsApp Cloud API support
    WHATSAPP_CLOUD_ACCESS_TOKEN: str | None = None
    WHATSAPP_CLOUD_PHONE_NUMBER_ID: str | None = None
    WHATSAPP_CLOUD_API_VERSION: str = "v20.0"

    # ---------------------------------------------------------
    # Uploads / Static files
    # ---------------------------------------------------------
    UPLOADS_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_EXTENSIONS: str = "jpg,jpeg,png,webp"

    # ---------------------------------------------------------
    # Business defaults
    # ---------------------------------------------------------
    DEFAULT_CURRENCY: str = "TZS"
    DEFAULT_SERVICE_TYPES: str = "cleaning,fumigation"

    # ---------------------------------------------------------
    # Logging
    # ---------------------------------------------------------
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def cors_origins(self) -> List[str]:
        """
        Converts comma-separated ALLOWED_ORIGINS from .env into a Python list.
        """
        if not self.ALLOWED_ORIGINS:
            return []

        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def allowed_image_extensions_list(self) -> List[str]:
        """
        Converts ALLOWED_IMAGE_EXTENSIONS into a clean list.

        Example:
            jpg,jpeg,png,webp -> ["jpg", "jpeg", "png", "webp"]
        """
        if not self.ALLOWED_IMAGE_EXTENSIONS:
            return []

        return [
            extension.strip().lower().replace(".", "")
            for extension in self.ALLOWED_IMAGE_EXTENSIONS.split(",")
            if extension.strip()
        ]

    @property
    def default_service_types_list(self) -> List[str]:
        """
        Converts DEFAULT_SERVICE_TYPES into a list.

        Example:
            cleaning,fumigation -> ["cleaning", "fumigation"]
        """
        if not self.DEFAULT_SERVICE_TYPES:
            return []

        return [
            item.strip().lower()
            for item in self.DEFAULT_SERVICE_TYPES.split(",")
            if item.strip()
        ]

    @property
    def max_upload_size_bytes(self) -> int:
        """
        Converts MAX_UPLOAD_SIZE_MB into bytes.
        """
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def is_development(self) -> bool:
        return self.APP_ENV.lower() == "development"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def email_configured(self) -> bool:
        """
        Checks if email has enough settings to send SMTP emails.
        """
        return bool(
            self.EMAIL_ENABLED
            and self.EMAIL_HOST
            and self.EMAIL_USERNAME
            and self.EMAIL_PASSWORD
            and self.EMAIL_FROM
        )

    @property
    def whatsapp_configured(self) -> bool:
        """
        Checks if manual WhatsApp links can be generated.
        """
        return bool(
            self.WHATSAPP_ENABLED
            and self.WHATSAPP_BUSINESS_NUMBER
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
