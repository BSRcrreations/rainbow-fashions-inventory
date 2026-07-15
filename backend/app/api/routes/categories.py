from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_manager_or_owner
from app.database.session import get_db
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.services.catalog_service import CategoryService


router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=list[CategoryRead])
def list_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list:
    return CategoryService(db).list(skip, limit)


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db), _: User = Depends(require_manager_or_owner)):
    return CategoryService(db).create(payload)


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(category_id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return CategoryService(db).get(category_id)


@router.put("/{category_id}", response_model=CategoryRead)
def update_category(category_id: UUID, payload: CategoryUpdate, db: Session = Depends(get_db), _: User = Depends(require_manager_or_owner)):
    return CategoryService(db).update(category_id, payload)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: UUID, db: Session = Depends(get_db), _: User = Depends(require_manager_or_owner)) -> Response:
    CategoryService(db).delete(category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
