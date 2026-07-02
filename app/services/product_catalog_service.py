import re
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.product import Product, ProductImage, ProductRequest
from app.models.user import User
from app.schemas.product import (
    ProductCreate,
    ProductImageCreate,
    ProductImageUpdate,
    ProductRequestCreate,
    ProductRequestStatusUpdate,
    ProductUpdate,
)
from app.services.file_storage_service import delete_local_file
from app.services.notification_message_service import build_whatsapp_link, notify_new_product_request, product_request_message


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "product"


def make_unique_product_slug(db: Session, name: str, preferred_slug: str | None = None, current_id: int | None = None) -> str:
    base_slug = slugify(preferred_slug or name)
    slug = base_slug
    counter = 2

    while True:
        query = db.query(Product).filter(Product.slug == slug)
        if current_id is not None:
            query = query.filter(Product.id != current_id)
        exists = query.first()
        if not exists:
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


def get_product_or_404(db: Session, product_id: int) -> Product:
    product = db.query(Product).options(selectinload(Product.images)).filter(Product.id == product_id).first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return product


def get_product_by_identifier_or_404(db: Session, identifier: str) -> Product:
    query = db.query(Product).options(selectinload(Product.images))

    if identifier.isdigit():
        product = query.filter(Product.id == int(identifier)).first()
    else:
        product = query.filter(Product.slug == identifier).first()

    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found.")
    return product


def list_products(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    category: str | None = None,
    is_active: bool | None = None,
    is_featured: bool | None = None,
    search: str | None = None,
) -> tuple[int, list[Product]]:
    query = db.query(Product).options(selectinload(Product.images))

    if category:
        query = query.filter(Product.category == category)
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)
    if is_featured is not None:
        query = query.filter(Product.is_featured == is_featured)
    if search:
        value = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Product.name.ilike(value),
                Product.category.ilike(value),
                Product.short_description.ilike(value),
                Product.description.ilike(value),
                Product.sku.ilike(value),
            )
        )

    total = query.count()
    items = query.order_by(Product.display_order.asc(), Product.created_at.desc()).offset(skip).limit(limit).all()
    return total, items


def create_product(db: Session, payload: ProductCreate, current_user: User | None = None) -> Product:
    data = payload.model_dump()
    data["slug"] = make_unique_product_slug(db, data["name"], data.get("slug"))
    data["created_by_user_id"] = current_user.id if current_user else None

    product = Product(**data)
    db.add(product)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A product with this slug or SKU already exists.")

    db.refresh(product)
    return get_product_or_404(db, product.id)


def update_product(db: Session, product_id: int, payload: ProductUpdate) -> Product:
    product = get_product_or_404(db, product_id)
    updates: dict[str, Any] = payload.model_dump(exclude_unset=True)

    if "name" in updates or "slug" in updates:
        name_for_slug = updates.get("name") or product.name
        preferred_slug = updates.get("slug") or product.slug
        updates["slug"] = make_unique_product_slug(db, name_for_slug, preferred_slug, current_id=product.id)

    for key, value in updates.items():
        setattr(product, key, value)

    db.add(product)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A product with this slug or SKU already exists.")

    db.refresh(product)
    return get_product_or_404(db, product.id)


def delete_product(db: Session, product_id: int) -> None:
    product = get_product_or_404(db, product_id)
    for image in list(product.images):
        delete_local_file(image.image_path)
    db.delete(product)
    db.commit()


def normalize_product_image_flags(data: dict[str, Any]) -> dict[str, Any]:
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


def add_product_image(
    db: Session,
    *,
    product_id: int,
    payload: ProductImageCreate,
    current_user: User | None = None,
) -> ProductImage:
    get_product_or_404(db, product_id)
    data = normalize_product_image_flags(payload.model_dump())
    data["product_id"] = product_id
    data["created_by_user_id"] = current_user.id if current_user else None

    if data.get("is_primary"):
        db.query(ProductImage).filter(ProductImage.product_id == product_id).update({"is_primary": False})
    if data.get("is_banner"):
        db.query(ProductImage).filter(ProductImage.product_id == product_id).update({"is_banner": False})

    image = ProductImage(**data)
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


def update_product_image(db: Session, image_id: int, payload: ProductImageUpdate) -> ProductImage:
    image = db.query(ProductImage).filter(ProductImage.id == image_id).first()
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product image not found.")

    updates = normalize_product_image_flags(payload.model_dump(exclude_unset=True))

    if updates.get("is_primary"):
        db.query(ProductImage).filter(ProductImage.product_id == image.product_id, ProductImage.id != image.id).update({"is_primary": False})
    if updates.get("is_banner"):
        db.query(ProductImage).filter(ProductImage.product_id == image.product_id, ProductImage.id != image.id).update({"is_banner": False})

    for key, value in updates.items():
        setattr(image, key, value)

    db.add(image)
    db.commit()
    db.refresh(image)
    return image


def delete_product_image(db: Session, image_id: int) -> None:
    image = db.query(ProductImage).filter(ProductImage.id == image_id).first()
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product image not found.")
    delete_local_file(image.image_path)
    db.delete(image)
    db.commit()


def create_product_request(db: Session, payload: ProductRequestCreate, current_user: User | None = None) -> ProductRequest:
    data = payload.model_dump()
    if data.get("product_id"):
        product = get_product_or_404(db, data["product_id"])
        data["product_name"] = product.name

    data["user_id"] = current_user.id if current_user else None
    request = ProductRequest(**data)
    db.add(request)
    db.commit()
    db.refresh(request)

    message = product_request_message(
        request_id=request.id,
        full_name=request.full_name,
        phone=request.phone,
        email=request.email,
        product_name=request.product_name,
        quantity=request.quantity,
        destination=request.destination,
    )
    request.whatsapp_link = build_whatsapp_link(message)
    db.add(request)
    db.commit()
    db.refresh(request)

    notification_result = notify_new_product_request(request)
    print("Product request notification result:", notification_result)

    return request


def list_product_requests(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    status_value: str | None = None,
    search: str | None = None,
    user_id: int | None = None,
) -> tuple[int, list[ProductRequest]]:
    query = db.query(ProductRequest)

    if user_id is not None:
        query = query.filter(ProductRequest.user_id == user_id)
    if status_value:
        query = query.filter(ProductRequest.status == status_value)
    if search:
        value = f"%{search.strip()}%"
        query = query.filter(
            or_(
                ProductRequest.full_name.ilike(value),
                ProductRequest.email.ilike(value),
                ProductRequest.phone.ilike(value),
                ProductRequest.company_name.ilike(value),
                ProductRequest.product_name.ilike(value),
            )
        )

    total = query.count()
    items = query.order_by(ProductRequest.created_at.desc()).offset(skip).limit(limit).all()
    return total, items


def get_product_request_or_404(db: Session, request_id: int) -> ProductRequest:
    request = db.query(ProductRequest).filter(ProductRequest.id == request_id).first()
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product request not found.")
    return request


def update_product_request_status(db: Session, request_id: int, payload: ProductRequestStatusUpdate) -> ProductRequest:
    request = get_product_request_or_404(db, request_id)
    request.status = payload.status
    if payload.admin_notes is not None:
        request.admin_notes = payload.admin_notes
    db.add(request)
    db.commit()
    db.refresh(request)
    return request
