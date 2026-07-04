from __future__ import annotations

from datetime import datetime, timezone
import secrets

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserCreateAdmin
from app.utils.security import hash_password, normalize_email, verify_password


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    cleaned_email = normalize_email(email)
    return db.query(User).filter(User.email == cleaned_email).first()


def get_user_by_phone(db: Session, phone: str) -> User | None:
    cleaned_phone = phone.strip()
    if not cleaned_phone:
        return None
    return db.query(User).filter(User.phone == cleaned_phone).first()


def create_user(db: Session, user_in: UserCreate | UserCreateAdmin) -> User:
    cleaned_email = normalize_email(str(user_in.email))
    cleaned_phone = user_in.phone.strip() if user_in.phone else None

    existing_user = db.query(User).filter(
        or_(
            User.email == cleaned_email,
            User.phone == cleaned_phone if cleaned_phone else False,
        )
    ).first()

    if existing_user:
        if existing_user.email == cleaned_email:
            detail = "A user with this email already exists."
        else:
            detail = "A user with this phone number already exists."

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )

    role = getattr(user_in, "role", UserRole.CUSTOMER.value)
    is_active = getattr(user_in, "is_active", True)
    is_verified = getattr(user_in, "is_verified", False)

    user = User(
        full_name=user_in.full_name.strip(),
        email=cleaned_email,
        phone=cleaned_phone,
        password_hash=hash_password(user_in.password),
        role=role,
        is_active=is_active,
        is_verified=is_verified,
    )

    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email or phone already exists.",
        )

    db.refresh(user)
    return user


def create_oauth_user(
    db: Session,
    *,
    email: str,
    full_name: str | None = None,
    role: str = UserRole.CUSTOMER.value,
) -> User:
    """
    Creates a user coming from Google OAuth.

    The current users table requires password_hash to be non-null, so this
    stores a random unusable password hash. The user can still reset password
    later through the normal forgot-password flow if that is implemented.
    """
    cleaned_email = normalize_email(email)
    existing_user = get_user_by_email(db, cleaned_email)
    if existing_user:
        return existing_user

    cleaned_name = (full_name or "").strip()
    if not cleaned_name:
        cleaned_name = cleaned_email.split("@")[0].replace(".", " ").title() or "Astra User"

    random_unusable_password = secrets.token_urlsafe(48)

    user = User(
        full_name=cleaned_name,
        email=cleaned_email,
        phone=None,
        password_hash=hash_password(random_unusable_password),
        role=role,
        is_active=True,
        is_verified=True,
    )

    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing_user = get_user_by_email(db, cleaned_email)
        if existing_user:
            return existing_user
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)

    if user is None:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def update_last_login(db: Session, user: User) -> User:
    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
) -> tuple[int, list[User]]:
    query = db.query(User)

    if search:
        search_value = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.full_name.ilike(search_value),
                User.email.ilike(search_value),
                User.phone.ilike(search_value),
            )
        )

    if role:
        query = query.filter(User.role == role)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()

    return total, users
