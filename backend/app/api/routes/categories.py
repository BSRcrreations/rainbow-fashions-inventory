from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_manager_or_owner
from app.database.session import get_db
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryHierarchyRead, CategoryRead, CategoryUpdate
from app.services.catalog_service import CategoryService


router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("/hierarchy", response_model=list[CategoryHierarchyRead])
def list_category_hierarchy(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list:
    return CategoryService(db).list_hierarchy(current_user, skip, limit)


@router.get("", response_model=list[CategoryRead])
def list_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list:
    return CategoryService(db).list(current_user, skip, limit)


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    return CategoryService(db).create(payload, current_user)


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(category_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return CategoryService(db).get(category_id, current_user)


@router.put("/{category_id}", response_model=CategoryRead)
def update_category(category_id: UUID, payload: CategoryUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    return CategoryService(db).update(category_id, payload, current_user)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)) -> Response:
    CategoryService(db).delete(category_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
