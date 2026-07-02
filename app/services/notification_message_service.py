from __future__ import annotations

from typing import Any
from urllib.parse import quote

from app.config import settings
from app.services.email_service import (
    send_admin_email,
    send_customer_confirmation_email,
)


# ============================================================
# Generic helpers
# ============================================================

def _get_value(source: Any, key: str, default: Any = None) -> Any:
    """
    Reads a value from a SQLAlchemy object or a dict.
    """
    if source is None:
        return default

    if isinstance(source, dict):
        return source.get(key, default)

    return getattr(source, key, default)


def _html_escape(value: Any) -> str:
    """
    Small safe HTML escape helper for notification emails.
    """
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#039;")
    )


# ============================================================
# WhatsApp
# ============================================================

def build_whatsapp_link(message: str, phone_number: str | None = None) -> str | None:
    """
    Builds a manual WhatsApp link that the frontend can open.

    Example:
        https://wa.me/255744094580?text=Hello...
    """
    number = phone_number or settings.WHATSAPP_BUSINESS_NUMBER

    if not settings.WHATSAPP_ENABLED:
        return None

    if not number:
        return None

    cleaned_number = "".join(character for character in number if character.isdigit())

    if not cleaned_number:
        return None

    return f"https://wa.me/{cleaned_number}?text={quote(message)}"


# ============================================================
# Service booking messages
# ============================================================

def service_booking_message(
    *,
    booking_id: int | None,
    full_name: str,
    phone: str | None,
    email: str | None,
    service_type: str,
    preferred_date: object | None,
    preferred_time: str | None,
    address: str | None,
) -> str:
    return "\n".join(
        [
            "New Astra Group service booking",
            f"Booking ID: {booking_id or 'Pending'}",
            f"Name: {full_name}",
            f"Phone: {phone or '-'}",
            f"Email: {email or '-'}",
            f"Service type: {service_type}",
            f"Preferred date: {preferred_date or '-'}",
            f"Preferred time: {preferred_time or '-'}",
            f"Address: {address or '-'}",
        ]
    )


def build_service_booking_admin_text(booking: Any) -> str:
    return f"""
New Service Booking Received

Booking ID: {_get_value(booking, "id", "")}
Customer Name: {_get_value(booking, "full_name", "")}
Email: {_get_value(booking, "email", "")}
Phone: {_get_value(booking, "phone", "")}
Company: {_get_value(booking, "company_name", "")}

Service ID: {_get_value(booking, "service_id", "")}
Service Type: {_get_value(booking, "service_type", "")}
Preferred Date: {_get_value(booking, "preferred_date", "")}
Preferred Time: {_get_value(booking, "preferred_time", "")}

Address: {_get_value(booking, "address", "")}
City: {_get_value(booking, "city", "")}

Message:
{_get_value(booking, "message", "")}

Status: {_get_value(booking, "status", "new")}
Source: {_get_value(booking, "source", "website")}
""".strip()


def build_service_booking_admin_html(booking: Any) -> str:
    rows = [
        ("Booking ID", _get_value(booking, "id", "")),
        ("Customer Name", _get_value(booking, "full_name", "")),
        ("Email", _get_value(booking, "email", "")),
        ("Phone", _get_value(booking, "phone", "")),
        ("Company", _get_value(booking, "company_name", "")),
        ("Service ID", _get_value(booking, "service_id", "")),
        ("Service Type", _get_value(booking, "service_type", "")),
        ("Preferred Date", _get_value(booking, "preferred_date", "")),
        ("Preferred Time", _get_value(booking, "preferred_time", "")),
        ("Address", _get_value(booking, "address", "")),
        ("City", _get_value(booking, "city", "")),
        ("Status", _get_value(booking, "status", "new")),
        ("Source", _get_value(booking, "source", "website")),
    ]

    rows_html = "".join(
        f"""
        <tr>
            <td style="padding:8px 12px;border:1px solid #e5e7eb;font-weight:600;">{_html_escape(label)}</td>
            <td style="padding:8px 12px;border:1px solid #e5e7eb;">{_html_escape(value)}</td>
        </tr>
        """
        for label, value in rows
    )

    message = _html_escape(_get_value(booking, "message", ""))

    return f"""
    <div style="font-family:Arial, sans-serif; color:#111827;">
        <h2 style="color:#0f766e;">New Service Booking Received</h2>
        <table style="border-collapse:collapse;width:100%;max-width:720px;">
            {rows_html}
        </table>
        <h3 style="margin-top:20px;">Message</h3>
        <p style="white-space:pre-wrap;background:#f9fafb;padding:12px;border:1px solid #e5e7eb;">{message}</p>
    </div>
    """


def build_service_booking_customer_text(booking: Any) -> str:
    name = _get_value(booking, "full_name", "Customer")
    service_type = _get_value(booking, "service_type", "service")

    return f"""
Dear {name},

Thank you for contacting Astra Group.

We have received your {service_type} booking request. Our team will review it and contact you shortly.

Regards,
Astra Group
""".strip()


def notify_new_service_booking(booking: Any) -> dict:
    """
    Sends admin and customer email notifications for new service booking.
    This function does not raise errors; it returns notification results.
    """
    try:
        admin_text = build_service_booking_admin_text(booking)
        admin_html = build_service_booking_admin_html(booking)
        customer_text = build_service_booking_customer_text(booking)

        admin_email_result = send_admin_email(
            subject="New Service Booking - Astra Group",
            text_body=admin_text,
            html_body=admin_html,
            reply_to=_get_value(booking, "email"),
        )

        customer_email_result = send_customer_confirmation_email(
            customer_email=_get_value(booking, "email"),
            subject="We received your service booking - Astra Group",
            text_body=customer_text,
        )

        return {
            "success": bool(admin_email_result.success),
            "admin_email": admin_email_result.__dict__,
            "customer_email": customer_email_result.__dict__,
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================
# Product request messages
# ============================================================

def product_request_message(
    *,
    request_id: int | None,
    full_name: str,
    phone: str | None,
    email: str | None,
    product_name: str,
    quantity: str | None,
    destination: str | None,
) -> str:
    return "\n".join(
        [
            "New Astra Group product request",
            f"Request ID: {request_id or 'Pending'}",
            f"Name: {full_name}",
            f"Phone: {phone or '-'}",
            f"Email: {email or '-'}",
            f"Product: {product_name}",
            f"Quantity: {quantity or '-'}",
            f"Destination: {destination or '-'}",
        ]
    )


def build_product_request_admin_text(product_request: Any) -> str:
    return f"""
New Product Request Received

Request ID: {_get_value(product_request, "id", "")}
Customer Name: {_get_value(product_request, "full_name", "")}
Email: {_get_value(product_request, "email", "")}
Phone: {_get_value(product_request, "phone", "")}
Company: {_get_value(product_request, "company_name", "")}

Product ID: {_get_value(product_request, "product_id", "")}
Product Name: {_get_value(product_request, "product_name", "")}
Quantity: {_get_value(product_request, "quantity", "")}
Destination: {_get_value(product_request, "destination", "")}
Delivery Required: {_get_value(product_request, "delivery_required", "")}

Message:
{_get_value(product_request, "message", "")}

Status: {_get_value(product_request, "status", "new")}
Source: {_get_value(product_request, "source", "website")}
""".strip()


def build_product_request_admin_html(product_request: Any) -> str:
    rows = [
        ("Request ID", _get_value(product_request, "id", "")),
        ("Customer Name", _get_value(product_request, "full_name", "")),
        ("Email", _get_value(product_request, "email", "")),
        ("Phone", _get_value(product_request, "phone", "")),
        ("Company", _get_value(product_request, "company_name", "")),
        ("Product ID", _get_value(product_request, "product_id", "")),
        ("Product Name", _get_value(product_request, "product_name", "")),
        ("Quantity", _get_value(product_request, "quantity", "")),
        ("Destination", _get_value(product_request, "destination", "")),
        ("Delivery Required", _get_value(product_request, "delivery_required", "")),
        ("Status", _get_value(product_request, "status", "new")),
        ("Source", _get_value(product_request, "source", "website")),
    ]

    rows_html = "".join(
        f"""
        <tr>
            <td style="padding:8px 12px;border:1px solid #e5e7eb;font-weight:600;">{_html_escape(label)}</td>
            <td style="padding:8px 12px;border:1px solid #e5e7eb;">{_html_escape(value)}</td>
        </tr>
        """
        for label, value in rows
    )

    message = _html_escape(_get_value(product_request, "message", ""))

    return f"""
    <div style="font-family:Arial, sans-serif; color:#111827;">
        <h2 style="color:#0f766e;">New Product Request Received</h2>
        <table style="border-collapse:collapse;width:100%;max-width:720px;">
            {rows_html}
        </table>
        <h3 style="margin-top:20px;">Message</h3>
        <p style="white-space:pre-wrap;background:#f9fafb;padding:12px;border:1px solid #e5e7eb;">{message}</p>
    </div>
    """


def build_product_request_customer_text(product_request: Any) -> str:
    name = _get_value(product_request, "full_name", "Customer")
    product_name = _get_value(product_request, "product_name", "product")

    return f"""
Dear {name},

Thank you for contacting Astra Group.

We have received your request for {product_name}. Our team will review it and contact you shortly.

Regards,
Astra Group
""".strip()


def notify_new_product_request(product_request: Any) -> dict:
    """
    Sends admin and customer email notifications for new product request.
    This function does not raise errors; it returns notification results.
    """
    try:
        admin_text = build_product_request_admin_text(product_request)
        admin_html = build_product_request_admin_html(product_request)
        customer_text = build_product_request_customer_text(product_request)

        admin_email_result = send_admin_email(
            subject="New Product Request - Astra Group",
            text_body=admin_text,
            html_body=admin_html,
            reply_to=_get_value(product_request, "email"),
        )

        customer_email_result = send_customer_confirmation_email(
            customer_email=_get_value(product_request, "email"),
            subject="We received your product request - Astra Group",
            text_body=customer_text,
        )

        return {
            "success": bool(admin_email_result.success),
            "admin_email": admin_email_result.__dict__,
            "customer_email": customer_email_result.__dict__,
        }

    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }
