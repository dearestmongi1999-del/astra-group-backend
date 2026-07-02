from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.banner import FrontendBanner
from app.models.user import User
from app.schemas.banner import FrontendBannerCreate, FrontendBannerUpdate
from app.services.file_storage_service import delete_local_file


def get_banner_or_404(db: Session, banner_id: int) -> FrontendBanner:
    banner = db.query(FrontendBanner).filter(FrontendBanner.id == banner_id).first()
    if banner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Banner not found.")
    return banner


def list_banners(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    banner_type: str | None = None,
    target_type: str | None = None,
    is_active: bool | None = None,
    active_now: bool = False,
    search: str | None = None,
) -> tuple[int, list[FrontendBanner]]:
    query = db.query(FrontendBanner)

    if banner_type:
        query = query.filter(FrontendBanner.banner_type == banner_type)
    if target_type:
        query = query.filter(FrontendBanner.target_type == target_type)
    if is_active is not None:
        query = query.filter(FrontendBanner.is_active == is_active)
    if active_now:
        now = datetime.now(timezone.utc)
        query = query.filter(FrontendBanner.is_active.is_(True))
        query = query.filter(or_(FrontendBanner.starts_at.is_(None), FrontendBanner.starts_at <= now))
        query = query.filter(or_(FrontendBanner.ends_at.is_(None), FrontendBanner.ends_at >= now))
    if search:
        value = f"%{search.strip()}%"
        query = query.filter(
            or_(
                FrontendBanner.title.ilike(value),
                FrontendBanner.subtitle.ilike(value),
                FrontendBanner.description.ilike(value),
            )
        )

    total = query.count()
    items = query.order_by(FrontendBanner.display_order.asc(), FrontendBanner.created_at.desc()).offset(skip).limit(limit).all()
    return total, items


def create_banner(db: Session, payload: FrontendBannerCreate, current_user: User | None = None) -> FrontendBanner:
    data = payload.model_dump()
    data["created_by_user_id"] = current_user.id if current_user else None
    banner = FrontendBanner(**data)
    db.add(banner)
    db.commit()
    db.refresh(banner)
    return banner


def update_banner(db: Session, banner_id: int, payload: FrontendBannerUpdate) -> FrontendBanner:
    banner = get_banner_or_404(db, banner_id)
    updates: dict[str, Any] = payload.model_dump(exclude_unset=True)

    for key, value in updates.items():
        setattr(banner, key, value)

    db.add(banner)
    db.commit()
    db.refresh(banner)
    return banner


def update_banner_image(
    db: Session,
    *,
    banner_id: int,
    image_url: str,
    image_path: str | None,
    original_filename: str | None,
    alt_text: str | None = None,
) -> FrontendBanner:
    banner = get_banner_or_404(db, banner_id)

    if banner.image_path and banner.image_path != image_path:
        delete_local_file(banner.image_path)

    banner.image_url = image_url
    banner.image_path = image_path
    banner.original_filename = original_filename
    if alt_text is not None:
        banner.alt_text = alt_text

    db.add(banner)
    db.commit()
    db.refresh(banner)
    return banner


def delete_banner(db: Session, banner_id: int) -> None:
    banner = get_banner_or_404(db, banner_id)
    delete_local_file(banner.image_path)
    db.delete(banner)
    db.commit()
