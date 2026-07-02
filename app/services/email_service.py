from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Iterable

from app.config import settings


@dataclass
class EmailSendResult:
    success: bool
    skipped: bool
    message: str
    recipients: list[str]


def _clean_recipients(recipients: str | Iterable[str] | None) -> list[str]:
    if recipients is None:
        return []

    if isinstance(recipients, str):
        raw_items = recipients.split(",")
    else:
        raw_items = list(recipients)

    return [item.strip() for item in raw_items if item and item.strip()]


def _email_is_configured() -> tuple[bool, str]:
    if not settings.EMAIL_ENABLED:
        return False, "Email is disabled. Set EMAIL_ENABLED=true to send real emails."

    required_values = {
        "EMAIL_HOST": settings.EMAIL_HOST,
        "EMAIL_USERNAME": settings.EMAIL_USERNAME,
        "EMAIL_PASSWORD": settings.EMAIL_PASSWORD,
        "EMAIL_FROM": settings.EMAIL_FROM,
    }

    missing = [key for key, value in required_values.items() if not value]

    if missing:
        return False, f"Email is not configured. Missing: {', '.join(missing)}"

    return True, "Email is configured."


def send_email(
    *,
    recipients: str | Iterable[str] | None,
    subject: str,
    text_body: str,
    html_body: str | None = None,
    reply_to: str | None = None,
) -> EmailSendResult:
    """
    Send an email through SMTP.

    If EMAIL_ENABLED=false, this does not fail. It returns skipped=True.
    This is useful during local development.
    """

    recipient_list = _clean_recipients(recipients)

    if not recipient_list:
        return EmailSendResult(
            success=False,
            skipped=False,
            message="No email recipients provided.",
            recipients=[],
        )

    configured, config_message = _email_is_configured()

    if not configured:
        return EmailSendResult(
            success=True,
            skipped=True,
            message=config_message,
            recipients=recipient_list,
        )

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
        msg["To"] = ", ".join(recipient_list)

        if reply_to:
            msg["Reply-To"] = reply_to

        msg.set_content(text_body)

        if html_body:
            msg.add_alternative(html_body, subtype="html")

        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
            smtp.send_message(msg)

        return EmailSendResult(
            success=True,
            skipped=False,
            message="Email sent successfully.",
            recipients=recipient_list,
        )

    except Exception as exc:
        return EmailSendResult(
            success=False,
            skipped=False,
            message=f"Email sending failed: {exc}",
            recipients=recipient_list,
        )


def send_admin_email(
    *,
    subject: str,
    text_body: str,
    html_body: str | None = None,
    reply_to: str | None = None,
) -> EmailSendResult:
    """
    Send notification email to Astra Group admin.
    """

    return send_email(
        recipients=settings.ADMIN_EMAIL,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        reply_to=reply_to,
    )


def send_customer_confirmation_email(
    *,
    customer_email: str | None,
    subject: str,
    text_body: str,
    html_body: str | None = None,
) -> EmailSendResult:
    """
    Send confirmation email to customer if customer email exists.
    """

    return send_email(
        recipients=customer_email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )
