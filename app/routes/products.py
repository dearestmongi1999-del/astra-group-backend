from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.product import (
    ProductCreate,
    ProductImageCreate,
    ProductImagePublic,
    ProductImageTypeValue,
    ProductImageUpdate,
    ProductListResponse,
    ProductPublic,
    ProductRequestCreate,
    ProductRequestListResponse,
    ProductRequestPublic,
    ProductRequestStatusUpdate,
    ProductUpdate,
)
from app.services.file_storage_service import save_upload_file
from app.services.product_catalog_service import (
    add_product_image,
    create_product,
    create_product_request,
    delete_product,
    delete_product_image,
    get_product_by_identifier_or_404,
    get_product_request_or_404,
    list_product_requests,
    list_products,
    update_product,
    update_product_image,
    update_product_request_status,
)
from app.utils.dependencies import get_current_active_user, get_current_staff_or_admin_user


router = APIRouter()
products_router = APIRouter(prefix="/products", tags=["Products"])
requests_router = APIRouter(prefix="/product-requests", tags=["Product Requests"])


@products_router.get("", response_model=ProductListResponse)
def get_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    category: str | None = None,
    is_active: bool | None = Query(default=True),
    is_featured: bool | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
) -> ProductListResponse:
    total, items = list_products(
        db,
        skip=skip,
        limit=limit,
        category=category,
        is_active=is_active,
        is_featured=is_featured,
        search=search,
    )
    return ProductListResponse(total=total, items=items)


@products_router.post("", response_model=ProductPublic, status_code=status.HTTP_201_CREATED)
def create_product_endpoint(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> ProductPublic:
    return ProductPublic.model_validate(create_product(db, payload, current_user))


@products_router.get("/{product_id_or_slug}", response_model=ProductPublic)
def get_product_detail(
    product_id_or_slug: str,
    db: Session = Depends(get_db),
) -> ProductPublic:
    return ProductPublic.model_validate(get_product_by_identifier_or_404(db, product_id_or_slug))


@products_router.patch("/{product_id}", response_model=ProductPublic)
def update_product_endpoint(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> ProductPublic:
    return ProductPublic.model_validate(update_product(db, product_id, payload))


@products_router.delete("/{product_id}", response_model=MessageResponse)
def delete_product_endpoint(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> MessageResponse:
    delete_product(db, product_id)
    return MessageResponse(success=True, message="Product deleted successfully.")


@products_router.post("/{product_id}/images", response_model=ProductImagePublic, status_code=status.HTTP_201_CREATED)
def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    alt_text: str | None = Form(default=None),
    image_type: ProductImageTypeValue = Form(default="gallery"),
    is_primary: bool = Form(default=False),
    is_banner: bool = Form(default=False),
    display_order: int = Form(default=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> ProductImagePublic:
    saved = save_upload_file(file, folder="products")
    image = add_product_image(
        db,
        product_id=product_id,
        payload=ProductImageCreate(
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
    return ProductImagePublic.model_validate(image)


@products_router.patch("/images/{image_id}", response_model=ProductImagePublic)
def update_product_image_endpoint(
    image_id: int,
    payload: ProductImageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> ProductImagePublic:
    return ProductImagePublic.model_validate(update_product_image(db, image_id, payload))


@products_router.delete("/images/{image_id}", response_model=MessageResponse)
def delete_product_image_endpoint(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> MessageResponse:
    delete_product_image(db, image_id)
    return MessageResponse(success=True, message="Product image deleted successfully.")


@requests_router.post("", response_model=ProductRequestPublic, status_code=status.HTTP_201_CREATED)
def create_product_request_endpoint(
    payload: ProductRequestCreate,
    db: Session = Depends(get_db),
) -> ProductRequestPublic:
    request = create_product_request(db, payload, current_user=None)
    return ProductRequestPublic.model_validate(request)


@requests_router.get("/my", response_model=ProductRequestListResponse)
def get_my_product_requests(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    status_value: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ProductRequestListResponse:
    total, items = list_product_requests(
        db,
        skip=skip,
        limit=limit,
        status_value=status_value,
        user_id=current_user.id,
    )
    return ProductRequestListResponse(total=total, items=items)


@requests_router.get("", response_model=ProductRequestListResponse)
def get_product_requests(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    status_value: str | None = Query(default=None, alias="status"),
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> ProductRequestListResponse:
    total, items = list_product_requests(
        db,
        skip=skip,
        limit=limit,
        status_value=status_value,
        search=search,
    )
    return ProductRequestListResponse(total=total, items=items)


@requests_router.get("/{request_id}", response_model=ProductRequestPublic)
def get_product_request_detail(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> ProductRequestPublic:
    return ProductRequestPublic.model_validate(get_product_request_or_404(db, request_id))


@requests_router.patch("/{request_id}/status", response_model=ProductRequestPublic)
def update_product_request_status_endpoint(
    request_id: int,
    payload: ProductRequestStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> ProductRequestPublic:
    return ProductRequestPublic.model_validate(update_product_request_status(db, request_id, payload))


router.include_router(products_router)
router.include_router(requests_router)
