from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_manager_or_owner, require_staff_or_above
from app.database.session import get_db
from app.models.sale import Sale
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerDetailRead, CustomerPaymentCreate, CustomerRead, CustomerUpdate
from app.schemas.sale import SaleRead
from app.services.business_service import CustomerService


router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("", response_model=list[CustomerRead])
def list_customers(search: Optional[str] = None, include_inactive: bool = False, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return CustomerService(db).list(current_user, search, include_inactive, skip, limit)


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db), current_user: User = Depends(require_staff_or_above)):
    return CustomerService(db).create(payload, current_user)


@router.get("/{customer_id}", response_model=CustomerDetailRead)
def get_customer(customer_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return CustomerService(db).detail(customer_id, current_user)


@router.put("/{customer_id}", response_model=CustomerRead)
def update_customer(customer_id: UUID, payload: CustomerUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_staff_or_above)):
    return CustomerService(db).update(customer_id, payload, current_user)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(customer_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)) -> Response:
    CustomerService(db).delete(customer_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{customer_id}/payments", response_model=CustomerDetailRead, status_code=status.HTTP_201_CREATED)
def add_customer_payment(customer_id: UUID, payload: CustomerPaymentCreate, db: Session = Depends(get_db), current_user: User = Depends(require_staff_or_above)):
    return CustomerService(db).add_payment(customer_id, payload, current_user)


@router.get("/{customer_id}/sales", response_model=list[SaleRead])
def customer_sales(customer_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    CustomerService(db).get(customer_id, current_user)
    return db.query(Sale).filter(Sale.store_id == current_user.store_id, Sale.customer_id == customer_id).order_by(Sale.sale_date.desc()).limit(100).all()
