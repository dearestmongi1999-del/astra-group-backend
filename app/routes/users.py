from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.user import (
    UserAdminUpdate,
    UserListResponse,
    UserPublic,
    UserStatusUpdate,
    UserUpdate,
)
from app.services.auth_service import get_user_by_id, list_users
from app.utils.dependencies import (
    get_current_active_user,
    get_current_admin_user,
    get_current_staff_or_admin_user,
)


router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=UserListResponse)
def get_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    search: str | None = Query(default=None),
    role: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> UserListResponse:
    total, users = list_users(
        db=db,
        skip=skip,
        limit=limit,
        search=search,
        role=role,
        is_active=is_active,
    )

    return UserListResponse(
        success=True,
        total=total,
        items=[UserPublic.model_validate(user) for user in users],
    )


@router.get("/me", response_model=UserPublic)
def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
) -> UserPublic:
    return UserPublic.model_validate(current_user)


@router.patch("/me", response_model=UserPublic)
def update_current_user_profile(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserPublic:
    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    return UserPublic.model_validate(current_user)


@router.get("/{user_id}", response_model=UserPublic)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> UserPublic:
    user = get_user_by_id(db, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    can_view = current_user.role in {"admin", "staff"} or current_user.id == user.id
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this user.",
        )

    return UserPublic.model_validate(user)


@router.patch("/{user_id}", response_model=UserPublic)
def update_user_as_admin_or_staff(
    user_id: int,
    payload: UserAdminUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_staff_or_admin_user),
) -> UserPublic:
    user = get_user_by_id(db, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    update_data = payload.model_dump(exclude_unset=True)

    if current_user.role != "admin":
        update_data.pop("role", None)
        update_data.pop("is_active", None)
        update_data.pop("is_verified", None)

    for field, value in update_data.items():
        setattr(user, field, value)

    db.add(user)
    db.commit()
    db.refresh(user)

    return UserPublic.model_validate(user)


@router.patch("/{user_id}/status", response_model=UserPublic)
def update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> UserPublic:
    user = get_user_by_id(db, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(user, field, value)

    db.add(user)
    db.commit()
    db.refresh(user)

    return UserPublic.model_validate(user)


@router.delete("/{user_id}", response_model=MessageResponse)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
) -> MessageResponse:
    user = get_user_by_id(db, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )

    user.is_active = False
    db.add(user)
    db.commit()

    return MessageResponse(
        success=True,
        message="User deactivated successfully.",
    )
