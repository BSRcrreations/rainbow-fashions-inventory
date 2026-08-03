from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_manager_or_owner, require_staff_or_above
from app.database.session import get_db
from app.models.user import User
from app.schemas.expense import ExpenseCategoryCreate, ExpenseCategoryRead, ExpenseCategoryUpdate, ExpenseCreate, ExpenseRead, ExpenseUpdate
from app.services.business_service import ExpenseService


router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.get("/categories", response_model=list[ExpenseCategoryRead])
def list_expense_categories(include_inactive: bool = False, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ExpenseService(db).list_categories(current_user, include_inactive)


@router.post("/categories", response_model=ExpenseCategoryRead, status_code=status.HTTP_201_CREATED)
def create_expense_category(payload: ExpenseCategoryCreate, db: Session = Depends(get_db), current_user: User = Depends(require_staff_or_above)):
    return ExpenseService(db).create_category(payload, current_user)


@router.put("/categories/{category_id}", response_model=ExpenseCategoryRead)
def update_expense_category(category_id: UUID, payload: ExpenseCategoryUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_staff_or_above)):
    return ExpenseService(db).update_category(category_id, payload, current_user)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense_category(category_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)) -> Response:
    ExpenseService(db).delete_category(category_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=list[ExpenseRead])
def list_expenses(start_date: Optional[date] = None, end_date: Optional[date] = None, category_id: Optional[UUID] = None, search: Optional[str] = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ExpenseService(db).list_expenses(current_user, start_date, end_date, category_id, search, skip, limit)


@router.post("", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
def create_expense(payload: ExpenseCreate, db: Session = Depends(get_db), current_user: User = Depends(require_staff_or_above)):
    return ExpenseService(db).create_expense(payload, current_user)


@router.get("/{expense_id}", response_model=ExpenseRead)
def get_expense(expense_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ExpenseService(db).get_expense(expense_id, current_user)


@router.put("/{expense_id}", response_model=ExpenseRead)
def update_expense(expense_id: UUID, payload: ExpenseUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_staff_or_above)):
    return ExpenseService(db).update_expense(expense_id, payload, current_user)


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)) -> Response:
    ExpenseService(db).delete_expense(expense_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
