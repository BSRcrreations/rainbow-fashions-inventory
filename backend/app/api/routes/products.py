from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_manager_or_owner
from app.database.session import get_db
from app.models.user import User
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services.product_service import ProductService


router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=list[ProductRead])
def list_products(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list:
    return ProductService(db).list(skip, limit, search)


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db), _: User = Depends(require_manager_or_owner)):
    return ProductService(db).create(payload)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(product_id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return ProductService(db).get(product_id)


@router.put("/{product_id}", response_model=ProductRead)
def update_product(product_id: UUID, payload: ProductUpdate, db: Session = Depends(get_db), _: User = Depends(require_manager_or_owner)):
    return ProductService(db).update(product_id, payload)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: UUID, db: Session = Depends(get_db), _: User = Depends(require_manager_or_owner)) -> Response:
    ProductService(db).delete(product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
