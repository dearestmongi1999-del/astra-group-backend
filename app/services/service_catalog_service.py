import re
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.service import Service, ServiceBooking, ServiceImage
from app.models.user import User
from app.schemas.service import (
    ServiceBookingCreate,
    ServiceBookingStatusUpdate,
    ServiceCreate,
    ServiceImageCreate,
    ServiceImageUpdate,
    ServiceUpdate,
)
from app.services.file_storage_service import delete_local_file
from app.services.notification_message_service import build_whatsapp_link, notify_new_service_booking, service_booking_message


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "service"


def make_unique_service_slug(db: Session, title: str, preferred_slug: str | None = None, current_id: int | None = None) -> str:
    base_slug = slugify(preferred_slug or title)
    slug = base_slug
    counter = 2

    while True:
        query = db.query(Service).filter(Service.slug == slug)
        if current_id is not None:
            query = query.filter(Service.id != current_id)
        exists = query.first()
        if not exists:
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


def get_service_or_404(db: Session, service_id: int) -> Service:
    service = db.query(Service).options(selectinload(Service.images)).filter(Service.id == service_id).first()
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found.")
    return service


def get_service_by_identifier_or_404(db: Session, identifier: str) -> Service:
    query = db.query(Service).options(selectinload(Service.images))

    if identifier.isdigit():
        service = query.filter(Service.id == int(identifier)).first()
    else:
        service = query.filter(Service.slug == identifier).first()

    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found.")
    return service


def list_services(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    service_type: str | None = None,
    is_active: bool | None = None,
    is_featured: bool | None = None,
    search: str | None = None,
) -> tuple[int, list[Service]]:
    query = db.query(Service).options(selectinload(Service.images))

    if service_type:
        query = query.filter(Service.service_type == service_type)
    if is_active is not None:
        query = query.filter(Service.is_active == is_active)
    if is_featured is not None:
        query = query.filter(Service.is_featured == is_featured)
    if search:
        value = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Service.title.ilike(value),
                Service.short_description.ilike(value),
                Service.description.ilike(value),
            )
        )

    total = query.count()
    items = (
        query.order_by(Service.display_order.asc(), Service.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return total, items


def create_service(db: Session, payload: ServiceCreate, current_user: User | None = None) -> Service:
    data = payload.model_dump()
    data["slug"] = make_unique_service_slug(db, data["title"], data.get("slug"))
    data["created_by_user_id"] = current_user.id if current_user else None

    service = Service(**data)
    db.add(service)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A service with this slug already exists.")

    db.refresh(service)
    return get_service_or_404(db, service.id)


def update_service(db: Session, service_id: int, payload: ServiceUpdate) -> Service:
    service = get_service_or_404(db, service_id)
    updates: dict[str, Any] = payload.model_dump(exclude_unset=True)

    if "title" in updates or "slug" in updates:
        title_for_slug = updates.get("title") or service.title
        preferred_slug = updates.get("slug") or service.slug
        updates["slug"] = make_unique_service_slug(db, title_for_slug, preferred_slug, current_id=service.id)

    for key, value in updates.items():
        setattr(service, key, value)

    db.add(service)
    db.commit()
    db.refresh(service)
    return get_service_or_404(db, service.id)


def delete_service(db: Session, service_id: int) -> None:
    service = get_service_or_404(db, service_id)
    for image in list(service.images):
        delete_local_file(image.image_path)
    db.delete(service)
    db.commit()


def normalize_service_image_flags(data: dict[str, Any]) -> dict[str, Any]:
    image_type = data.get("image_type") or "gallery"
    if image_type == "primary":
        data["is_primary"] = True
    if image_type == "banner":
        data["is_banner"] = True
    if data.get("is_primary"):
        data["image_type"] = "primary"
    elif data.get("is_banner"):
        data["image_type"] = "banner"
    return data


def add_service_image(
    db: Session,
    *,
    service_id: int,
    payload: ServiceImageCreate,
    current_user: User | None = None,
) -> ServiceImage:
    get_service_or_404(db, service_id)
    data = normalize_service_image_flags(payload.model_dump())
    data["service_id"] = service_id
    data["created_by_user_id"] = current_user.id if current_user else None

    if data.get("is_primary"):
        db.query(ServiceImage).filter(ServiceImage.service_id == service_id).update({"is_primary": False})
    if data.get("is_banner"):
        db.query(ServiceImage).filter(ServiceImage.service_id == service_id).update({"is_banner": False})

    image = ServiceImage(**data)
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


def update_service_image(db: Session, image_id: int, payload: ServiceImageUpdate) -> ServiceImage:
    image = db.query(ServiceImage).filter(ServiceImage.id == image_id).first()
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service image not found.")

    updates = normalize_service_image_flags(payload.model_dump(exclude_unset=True))

    if updates.get("is_primary"):
        db.query(ServiceImage).filter(ServiceImage.service_id == image.service_id, ServiceImage.id != image.id).update({"is_primary": False})
    if updates.get("is_banner"):
        db.query(ServiceImage).filter(ServiceImage.service_id == image.service_id, ServiceImage.id != image.id).update({"is_banner": False})

    for key, value in updates.items():
        setattr(image, key, value)

    db.add(image)
    db.commit()
    db.refresh(image)
    return image


def delete_service_image(db: Session, image_id: int) -> None:
    image = db.query(ServiceImage).filter(ServiceImage.id == image_id).first()
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service image not found.")
    delete_local_file(image.image_path)
    db.delete(image)
    db.commit()


def create_service_booking(db: Session, payload: ServiceBookingCreate, current_user: User | None = None) -> ServiceBooking:
    data = payload.model_dump()
    service = None
    if data.get("service_id"):
        service = get_service_or_404(db, data["service_id"])
        data["service_type"] = service.service_type

    data["user_id"] = current_user.id if current_user else None
    booking = ServiceBooking(**data)
    db.add(booking)
    db.commit()
    db.refresh(booking)

    message = service_booking_message(
        booking_id=booking.id,
        full_name=booking.full_name,
        phone=booking.phone,
        email=booking.email,
        service_type=booking.service_type,
        preferred_date=booking.preferred_date,
        preferred_time=booking.preferred_time,
        address=booking.address,
    )
    booking.whatsapp_link = build_whatsapp_link(message)
    db.add(booking)
    db.commit()
    db.refresh(booking)

    notification_result = notify_new_service_booking(booking)
    print("Service booking notification result:", notification_result)

    return booking


def list_service_bookings(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    status_value: str | None = None,
    service_type: str | None = None,
    search: str | None = None,
    user_id: int | None = None,
) -> tuple[int, list[ServiceBooking]]:
    query = db.query(ServiceBooking)

    if user_id is not None:
        query = query.filter(ServiceBooking.user_id == user_id)
    if status_value:
        query = query.filter(ServiceBooking.status == status_value)
    if service_type:
        query = query.filter(ServiceBooking.service_type == service_type)
    if search:
        value = f"%{search.strip()}%"
        query = query.filter(
            or_(
                ServiceBooking.full_name.ilike(value),
                ServiceBooking.email.ilike(value),
                ServiceBooking.phone.ilike(value),
                ServiceBooking.company_name.ilike(value),
            )
        )

    total = query.count()
    items = query.order_by(ServiceBooking.created_at.desc()).offset(skip).limit(limit).all()
    return total, items


def get_service_booking_or_404(db: Session, booking_id: int) -> ServiceBooking:
    booking = db.query(ServiceBooking).filter(ServiceBooking.id == booking_id).first()
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service booking not found.")
    return booking


def update_service_booking_status(db: Session, booking_id: int, payload: ServiceBookingStatusUpdate) -> ServiceBooking:
    booking = get_service_booking_or_404(db, booking_id)
    booking.status = payload.status
    if payload.admin_notes is not None:
        booking.admin_notes = payload.admin_notes
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking
