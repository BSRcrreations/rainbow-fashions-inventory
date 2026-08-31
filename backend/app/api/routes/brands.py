from __future__ import annotations

from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_manager_or_owner, require_owner
from app.database.session import get_db
from app.models.user import User
from app.schemas.brand import BrandCreate, BrandRead, BrandUpdate
from app.services.catalog_service import BrandService


router = APIRouter(prefix="/brands", tags=["Brands"])


@router.get("", response_model=list[BrandRead])
def list_brands(category_id: Optional[UUID] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list:
    return BrandService(db).list(current_user, category_id, skip, limit)


@router.post("", response_model=BrandRead, status_code=status.HTTP_201_CREATED)
def create_brand(payload: BrandCreate, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    return BrandService(db).create(payload, current_user)


@router.get("/{brand_id}", response_model=BrandRead)
def get_brand(brand_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return BrandService(db).get(brand_id, current_user)


@router.put("/{brand_id}", response_model=BrandRead)
def update_brand(brand_id: UUID, payload: BrandUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    return BrandService(db).update(brand_id, payload, current_user)


@router.post("/{brand_id}/logo", response_model=BrandRead)
async def upload_brand_logo(
    brand_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_owner),
):
    return await BrandService(db).upload_logo(brand_id, file, current_user)


@router.delete("/{brand_id}/logo", response_model=BrandRead)
def delete_brand_logo(brand_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    return BrandService(db).delete_logo(brand_id, current_user)


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_brand(brand_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_owner)) -> Response:
    BrandService(db).delete(brand_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
