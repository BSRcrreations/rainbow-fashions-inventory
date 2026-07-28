from __future__ import annotations

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_manager_or_owner
from app.database.session import get_db
from app.models.user import User
from app.schemas.subcategory import SubCategoryCreate, SubCategoryRead, SubCategoryUpdate
from app.services.catalog_service import SubCategoryService


router = APIRouter(prefix="/subcategories", tags=["Subcategories"])


@router.get("", response_model=list[SubCategoryRead])
def list_subcategories(category_id: Optional[UUID] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list:
    return SubCategoryService(db).list(current_user, category_id, skip, limit)


@router.post("", response_model=SubCategoryRead, status_code=status.HTTP_201_CREATED)
def create_subcategory(payload: SubCategoryCreate, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    return SubCategoryService(db).create(payload, current_user)


@router.put("/{subcategory_id}", response_model=SubCategoryRead)
def update_subcategory(subcategory_id: UUID, payload: SubCategoryUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    return SubCategoryService(db).update(subcategory_id, payload, current_user)


@router.delete("/{subcategory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subcategory(subcategory_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)) -> Response:
    SubCategoryService(db).delete(subcategory_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
