from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.service import (
    ServiceBookingCreate,
    ServiceBookingListResponse,
    ServiceBookingPublic,
    ServiceBookingStatusUpdate,
    ServiceCreate,
    ServiceImageCreate,
    ServiceImagePublic,
    ServiceImageTypeValue,
    ServiceImageUpdate,
    ServiceListResponse,
    ServicePublic,
    ServiceTypeValue,
    ServiceUpdate,
)
from app.services.file_storage_service import save_upload_file
from app.services.service_catalog_service import (
    add_service_image,
    create_service,
    create_service_booking,
    delete_service,
    delete_service_image,
    get_service_booking_or_404,
    get_service_by_identifier_or_404,
    list_service_bookings,
    list_services,
    update_service,
    update_service_booking_status,
    update_service_image,
)
from app.utils.dependencies import get_current_active_user, get_current_staff_or_admin_user


router = APIRouter()
services_router = APIRouter(prefix="/services", tags=["Services"])
bookings_router = APIRouter(prefix="/service-bookings", tags=["Service Bookings"])


@services_router.get("/types")
def get_service_types() -> dict:
    return {
        "success": True,
        "items": [
            {"value": "cleaning", "label": "Cleaning"},
            {"value": "fumigation", "label": "Fumigation"},
        ],
    }


@services_router.get("", response_model=ServiceListResponse)
def get_services(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    service_type: ServiceTypeValue | None = None,
    is_active: bool | None = Query(default=True),
    is_featured: bool | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
) -> ServiceListResponse:
    total, items = list_services(
        db,
        skip=skip,
        limit=limit,
        service_type=service_type,
        is_active=is_active,
        is_featured=is_featured,
        search=search,
    )
    return ServiceListResponse(total=total, items=items)


@services_router.post("", response_model=ServicePublic, status_code=status.HTTP_201_CREATED)
def create_service_endpoint(
    payload: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> ServicePublic:
    return ServicePublic.model_validate(create_service(db, payload, current_user))


@services_router.get("/{service_id_or_slug}", response_model=ServicePublic)
def get_service_detail(
    service_id_or_slug: str,
    db: Session = Depends(get_db),
) -> ServicePublic:
    return ServicePublic.model_validate(get_service_by_identifier_or_404(db, service_id_or_slug))


@services_router.patch("/{service_id}", response_model=ServicePublic)
def update_service_endpoint(
    service_id: int,
    payload: ServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> ServicePublic:
    return ServicePublic.model_validate(update_service(db, service_id, payload))


@services_router.delete("/{service_id}", response_model=MessageResponse)
def delete_service_endpoint(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> MessageResponse:
    delete_service(db, service_id)
    return MessageResponse(success=True, message="Service deleted successfully.")


@services_router.post("/{service_id}/images", response_model=ServiceImagePublic, status_code=status.HTTP_201_CREATED)
def upload_service_image(
    service_id: int,
    file: UploadFile = File(...),
    alt_text: str | None = Form(default=None),
    image_type: ServiceImageTypeValue = Form(default="gallery"),
    is_primary: bool = Form(default=False),
    is_banner: bool = Form(default=False),
    display_order: int = Form(default=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> ServiceImagePublic:
    saved = save_upload_file(file, folder="services")
    image = add_service_image(
        db,
        service_id=service_id,
        payload=ServiceImageCreate(
            image_url=saved["image_url"],
            image_path=saved["image_path"],
            original_filename=saved["original_filename"],
            alt_text=alt_text,
            image_type=image_type,
            is_primary=is_primary,
            is_banner=is_banner,
            display_order=display_order,
        ),
        current_user=current_user,
    )
    return ServiceImagePublic.model_validate(image)


@services_router.patch("/images/{image_id}", response_model=ServiceImagePublic)
def update_service_image_endpoint(
    image_id: int,
    payload: ServiceImageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> ServiceImagePublic:
    return ServiceImagePublic.model_validate(update_service_image(db, image_id, payload))


@services_router.delete("/images/{image_id}", response_model=MessageResponse)
def delete_service_image_endpoint(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> MessageResponse:
    delete_service_image(db, image_id)
    return MessageResponse(success=True, message="Service image deleted successfully.")


@bookings_router.post("", response_model=ServiceBookingPublic, status_code=status.HTTP_201_CREATED)
def create_service_booking_endpoint(
    payload: ServiceBookingCreate,
    db: Session = Depends(get_db),
) -> ServiceBookingPublic:
    booking = create_service_booking(db, payload, current_user=None)
    return ServiceBookingPublic.model_validate(booking)


@bookings_router.get("/my", response_model=ServiceBookingListResponse)
def get_my_service_bookings(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    status_value: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ServiceBookingListResponse:
    total, items = list_service_bookings(
        db,
        skip=skip,
        limit=limit,
        status_value=status_value,
        user_id=current_user.id,
    )
    return ServiceBookingListResponse(total=total, items=items)


@bookings_router.get("", response_model=ServiceBookingListResponse)
def get_service_bookings(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    status_value: str | None = Query(default=None, alias="status"),
    service_type: ServiceTypeValue | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> ServiceBookingListResponse:
    total, items = list_service_bookings(
        db,
        skip=skip,
        limit=limit,
        status_value=status_value,
        service_type=service_type,
        search=search,
    )
    return ServiceBookingListResponse(total=total, items=items)


@bookings_router.get("/{booking_id}", response_model=ServiceBookingPublic)
def get_service_booking_detail(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> ServiceBookingPublic:
    return ServiceBookingPublic.model_validate(get_service_booking_or_404(db, booking_id))


@bookings_router.patch("/{booking_id}/status", response_model=ServiceBookingPublic)
def update_service_booking_status_endpoint(
    booking_id: int,
    payload: ServiceBookingStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> ServiceBookingPublic:
    return ServiceBookingPublic.model_validate(update_service_booking_status(db, booking_id, payload))


router.include_router(services_router)
router.include_router(bookings_router)
