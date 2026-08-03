from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.report import BusinessReportsSummary, InventoryValuationReport
from app.services.report_service import ReportService


router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/summary", response_model=BusinessReportsSummary)
def reports_summary(start_date: Optional[date] = None, end_date: Optional[date] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ReportService(db).summary(current_user, start_date, end_date)


@router.get("/inventory-valuation", response_model=InventoryValuationReport)
def inventory_valuation(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ReportService(db).inventory_valuation(current_user)
