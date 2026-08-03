from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_manager_or_owner, require_staff_or_above
from app.database.session import get_db
from app.models.purchase import Purchase
from app.models.user import User
from app.schemas.purchase import PurchaseRead
from app.schemas.supplier import SupplierCreate, SupplierDetailRead, SupplierPaymentCreate, SupplierRead, SupplierUpdate
from app.services.business_service import SupplierService


router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


@router.get("", response_model=list[SupplierRead])
def list_suppliers(search: Optional[str] = None, include_inactive: bool = False, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return SupplierService(db).list(current_user, search, include_inactive, skip, limit)


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
def create_supplier(payload: SupplierCreate, db: Session = Depends(get_db), current_user: User = Depends(require_staff_or_above)):
    return SupplierService(db).create(payload, current_user)


@router.get("/{supplier_id}", response_model=SupplierDetailRead)
def get_supplier(supplier_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return SupplierService(db).detail(supplier_id, current_user)


@router.put("/{supplier_id}", response_model=SupplierRead)
def update_supplier(supplier_id: UUID, payload: SupplierUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_staff_or_above)):
    return SupplierService(db).update(supplier_id, payload, current_user)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(supplier_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)) -> Response:
    SupplierService(db).delete(supplier_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{supplier_id}/payments", response_model=SupplierDetailRead, status_code=status.HTTP_201_CREATED)
def add_supplier_payment(supplier_id: UUID, payload: SupplierPaymentCreate, db: Session = Depends(get_db), current_user: User = Depends(require_staff_or_above)):
    return SupplierService(db).add_payment(supplier_id, payload, current_user)


@router.get("/{supplier_id}/purchases", response_model=list[PurchaseRead])
def supplier_purchases(supplier_id: UUID, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    SupplierService(db).get(supplier_id, current_user)
    return db.query(Purchase).filter(Purchase.store_id == current_user.store_id, Purchase.supplier_id == supplier_id).order_by(Purchase.purchase_date.desc(), Purchase.created_at.desc()).offset(skip).limit(limit).all()
