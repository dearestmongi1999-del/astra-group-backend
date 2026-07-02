import base64
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.config import settings


# ============================================================
# General helpers
# ============================================================

def normalize_email(email: str) -> str:
    """
    Normalize email before saving or comparing.

    Keeps auth consistent by removing spaces and lowercasing.
    """

    if not email:
        return ""

    return email.strip().lower()


def is_password_strong_enough(password: str) -> bool:
    """
    Basic password strength validation.

    Requirement:
    - At least 8 characters
    - At least one letter
    - At least one number
    """

    if not password:
        return False

    if len(password) < 8:
        return False

    has_letter = bool(re.search(r"[A-Za-z]", password))
    has_number = bool(re.search(r"\d", password))

    return has_letter and has_number


# ============================================================
# Password hashing
# ============================================================
# We use PBKDF2-SHA256 from Python standard library.
# This avoids bcrypt/passlib compatibility issues on Vercel.
#
# Stored format:
#   pbkdf2_sha256$390000$salt_base64$hash_base64
# ============================================================

PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 390000
SALT_BYTES = 16


def _b64_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _b64_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str) -> str:
    """
    Hash a plain password using PBKDF2-SHA256.
    """

    if not password:
        raise ValueError("Password cannot be empty.")

    salt = secrets.token_bytes(SALT_BYTES)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )

    return (
        f"{PASSWORD_HASH_ALGORITHM}"
        f"${PBKDF2_ITERATIONS}"
        f"${_b64_encode(salt)}"
        f"${_b64_encode(password_hash)}"
    )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against the stored password hash.
    """

    if not plain_password or not hashed_password:
        return False

    try:
        parts = hashed_password.split("$")

        if len(parts) != 4:
            return False

        algorithm, iterations_text, salt_text, hash_text = parts

        if algorithm != PASSWORD_HASH_ALGORITHM:
            return False

        iterations = int(iterations_text)
        salt = _b64_decode(salt_text)
        expected_hash = _b64_decode(hash_text)

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt,
            iterations,
        )

        return hmac.compare_digest(actual_hash, expected_hash)

    except Exception:
        return False


# Backward-compatible aliases in case any file uses old names later.
get_password_hash = hash_password


# ============================================================
# JWT helpers
# ============================================================

def create_access_token(
    *,
    subject: str | int,
    email: str | None = None,
    role: str | None = None,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create JWT access token.
    """

    now = datetime.now(timezone.utc)

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = now + expires_delta

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }

    if email:
        payload["email"] = normalize_email(email)

    if role:
        payload["role"] = role

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any] | None:
    """
    Decode and validate JWT access token.
    """

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        if payload.get("type") != "access":
            return None

        return payload

    except JWTError:
        return None
