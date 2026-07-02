from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a plain-text password before saving it in the database.
    """
    return password_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compare a plain-text password with the stored password hash.
    """
    return password_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        subject: Usually the user ID as a string.
        expires_delta: Optional custom expiry.
        extra_claims: Optional extra data such as email and role.
    """
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": expire,
        "type": "access",
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Raises JWTError if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        raise

    token_type = payload.get("type")
    if token_type != "access":
        raise JWTError("Invalid token type.")

    return payload


def normalize_email(email: str) -> str:
    """
    Normalize email addresses before saving or comparing.
    """
    return email.strip().lower()


def is_password_strong_enough(password: str) -> bool:
    """
    Basic password strength check.
    Keeps local development simple while preventing extremely weak passwords.
    """
    if len(password) < 8:
        return False

    has_letter = any(character.isalpha() for character in password)
    has_number = any(character.isdigit() for character in password)

    return has_letter and has_number
