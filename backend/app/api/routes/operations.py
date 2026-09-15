from typing import Optional
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_cashier, require_manager_or_owner, require_owner, require_report_reader
from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import UserRead
from app.schemas.operations import AuditPage, DayClosingCreate, DayClosingRead, DayClosingSummary, PrinterSettings, StoreSettings, UserCreate, UserUpdate
from app.services.operations_service import OperationsService


router = APIRouter(tags=["Shop operations"])


@router.get("/settings/store", response_model=StoreSettings)
def settings(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return OperationsService(db).settings(user)


@router.put("/settings/store", response_model=StoreSettings)
def save_settings(payload: StoreSettings, request: Request, db: Session = Depends(get_db), user: User = Depends(require_owner)):
    return OperationsService(db).save_settings(payload, user, request.state.request_id)


@router.put("/settings/printers", response_model=StoreSettings)
def save_printers(payload: PrinterSettings, request: Request, db: Session = Depends(get_db), user: User = Depends(require_manager_or_owner)):
    return OperationsService(db).save_settings(payload, user, request.state.request_id)


@router.get("/users", response_model=list[UserRead])
def users(skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100), db: Session = Depends(get_db), user: User = Depends(require_owner)):
    return OperationsService(db).users(user, skip, limit)


@router.post("/users", response_model=UserRead, status_code=201)
def create_user(payload: UserCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_owner)):
    return OperationsService(db).create_user(payload, user, request.state.request_id)


@router.put("/users/{user_id}", response_model=UserRead)
def update_user(user_id: UUID, payload: UserUpdate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_owner)):
    return OperationsService(db).update_user(user_id, payload, user, request.state.request_id)


@router.get("/day-closing/preview", response_model=DayClosingSummary)
def closing_preview(business_date: date, opening_cash: Decimal = Query(Decimal("0"), ge=0, le=999999999999), db: Session = Depends(get_db), user: User = Depends(require_cashier)):
    return OperationsService(db).closing_preview(user, business_date, opening_cash)


@router.get("/day-closing", response_model=list[DayClosingRead])
def closings(skip: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100), start_date: Optional[date] = None, end_date: Optional[date] = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Read-only reporting is also available to the accountant and viewer.
    if user.role.value not in ("OWNER", "MANAGER", "CASHIER", "STAFF", "ACCOUNTANT", "VIEWER"):
        from app.core.exceptions import forbidden
        raise forbidden("Your role cannot view cash closing reports.")
    return OperationsService(db).closings(user, skip, limit, start_date, end_date)


@router.post("/day-closing", response_model=DayClosingRead)
def submit_closing(payload: DayClosingCreate, request: Request, db: Session = Depends(get_db), user: User = Depends(require_cashier)):
    return OperationsService(db).submit_closing(payload, user, request.state.request_id)


@router.post("/day-closing/{closing_id}/approve", response_model=DayClosingRead)
def approve_closing(closing_id: UUID, request: Request, db: Session = Depends(get_db), user: User = Depends(require_manager_or_owner)):
    return OperationsService(db).approve_closing(closing_id, user, request.state.request_id)


@router.get("/audit-log", response_model=AuditPage)
def audit_log(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), search: Optional[str] = Query(None, max_length=120), start_date: Optional[date] = None, end_date: Optional[date] = None, db: Session = Depends(get_db), user: User = Depends(require_report_reader)):
    return OperationsService(db).audit_log(user, skip, limit, search, start_date, end_date)
