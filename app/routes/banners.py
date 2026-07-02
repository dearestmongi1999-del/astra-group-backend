from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.banner import (
    BannerTargetTypeValue,
    BannerTypeValue,
    FrontendBannerCreate,
    FrontendBannerListResponse,
    FrontendBannerPublic,
    FrontendBannerUpdate,
)
from app.services.banner_service import create_banner, delete_banner, get_banner_or_404, list_banners, update_banner, update_banner_image
from app.services.file_storage_service import save_upload_file
from app.utils.dependencies import get_current_staff_or_admin_user


router = APIRouter(prefix="/banners", tags=["Frontend Banners"])


@router.get("", response_model=FrontendBannerListResponse)
def get_banners(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    banner_type: BannerTypeValue | None = None,
    target_type: BannerTargetTypeValue | None = None,
    is_active: bool | None = Query(default=True),
    active_now: bool = Query(default=True),
    search: str | None = None,
    db: Session = Depends(get_db),
) -> FrontendBannerListResponse:
    total, items = list_banners(
        db,
        skip=skip,
        limit=limit,
        banner_type=banner_type,
        target_type=target_type,
        is_active=is_active,
        active_now=active_now,
        search=search,
    )
    return FrontendBannerListResponse(total=total, items=items)


@router.post("", response_model=FrontendBannerPublic, status_code=status.HTTP_201_CREATED)
def create_banner_endpoint(
    payload: FrontendBannerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> FrontendBannerPublic:
    return FrontendBannerPublic.model_validate(create_banner(db, payload, current_user))


@router.get("/{banner_id}", response_model=FrontendBannerPublic)
def get_banner_detail(
    banner_id: int,
    db: Session = Depends(get_db),
) -> FrontendBannerPublic:
    return FrontendBannerPublic.model_validate(get_banner_or_404(db, banner_id))


@router.patch("/{banner_id}", response_model=FrontendBannerPublic)
def update_banner_endpoint(
    banner_id: int,
    payload: FrontendBannerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> FrontendBannerPublic:
    return FrontendBannerPublic.model_validate(update_banner(db, banner_id, payload))


@router.delete("/{banner_id}", response_model=MessageResponse)
def delete_banner_endpoint(
    banner_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> MessageResponse:
    delete_banner(db, banner_id)
    return MessageResponse(success=True, message="Banner deleted successfully.")


@router.post("/{banner_id}/image", response_model=FrontendBannerPublic)
def upload_banner_image(
    banner_id: int,
    file: UploadFile = File(...),
    alt_text: str | None = Form(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> FrontendBannerPublic:
    saved = save_upload_file(file, folder="banners")
    banner = update_banner_image(
        db,
        banner_id=banner_id,
        image_url=saved["image_url"],
        image_path=saved["image_path"],
        original_filename=saved["original_filename"],
        alt_text=alt_text,
    )
    return FrontendBannerPublic.model_validate(banner)
