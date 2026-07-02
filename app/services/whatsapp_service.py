from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from app.config import settings


@dataclass
class WhatsAppResult:
    success: bool
    skipped: bool
    message: str
    phone_number: str | None
    whatsapp_link: str | None


def clean_phone_number(phone_number: str | None) -> str | None:
    """
    Converts phone number into wa.me-friendly format.

    Example:
        +255 744 094 580 -> 255744094580
    """

    if not phone_number:
        return None

    cleaned = (
        phone_number.replace("+", "")
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )

    return cleaned or None


def build_whatsapp_link(*, phone_number: str | None, message: str) -> str | None:
    """
    Creates a manual WhatsApp link.

    The frontend can open this link to send the message manually.
    """

    cleaned_number = clean_phone_number(phone_number)

    if not cleaned_number:
        return None

    encoded_message = quote(message)
    return f"https://wa.me/{cleaned_number}?text={encoded_message}"


def build_admin_whatsapp_link(message: str) -> WhatsAppResult:
    """
    Creates WhatsApp link for Astra Group business/admin number.
    """

    if not settings.WHATSAPP_ENABLED:
        return WhatsAppResult(
            success=True,
            skipped=True,
            message="WhatsApp is disabled.",
            phone_number=settings.WHATSAPP_BUSINESS_NUMBER,
            whatsapp_link=None,
        )

    link = build_whatsapp_link(
        phone_number=settings.WHATSAPP_BUSINESS_NUMBER,
        message=message,
    )

    if not link:
        return WhatsAppResult(
            success=False,
            skipped=False,
            message="WhatsApp business number is missing or invalid.",
            phone_number=settings.WHATSAPP_BUSINESS_NUMBER,
            whatsapp_link=None,
        )

    return WhatsAppResult(
        success=True,
        skipped=False,
        message="WhatsApp link created successfully.",
        phone_number=clean_phone_number(settings.WHATSAPP_BUSINESS_NUMBER),
        whatsapp_link=link,
    )


def build_customer_whatsapp_link(*, customer_phone: str | None, message: str) -> WhatsAppResult:
    """
    Creates WhatsApp link for contacting a customer.
    """

    if not settings.WHATSAPP_ENABLED:
        return WhatsAppResult(
            success=True,
            skipped=True,
            message="WhatsApp is disabled.",
            phone_number=customer_phone,
            whatsapp_link=None,
        )

    link = build_whatsapp_link(
        phone_number=customer_phone,
        message=message,
    )

    if not link:
        return WhatsAppResult(
            success=False,
            skipped=False,
            message="Customer WhatsApp number is missing or invalid.",
            phone_number=customer_phone,
            whatsapp_link=None,
        )

    return WhatsAppResult(
        success=True,
        skipped=False,
        message="Customer WhatsApp link created successfully.",
        phone_number=clean_phone_number(customer_phone),
        whatsapp_link=link,
    )
