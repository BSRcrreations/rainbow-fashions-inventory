from __future__ import annotations

from datetime import date
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import error_payload
from app.database.session import get_db
from app.models.user import User
from app.schemas.report import BusinessReportsSummary, InventoryValuationReport
from app.services.report_service import ReportService


router = APIRouter(prefix="/reports", tags=["Reports"])
logger = logging.getLogger(__name__)


@router.get("/summary", response_model=BusinessReportsSummary)
def reports_summary(request: Request, start_date: Optional[date] = None, end_date: Optional[date] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    request_id = request.state.request_id
    try:
        return ReportService(db).summary(current_user, start_date, end_date, request_id)
    except SQLAlchemyError as exc:
        # Keep diagnostics in the server logs and return a stable, safe API
        # contract.  The request ID lets support locate the full exception.
        logger.exception(
            "reports_summary_failed request_id=%s exception_type=%s start_date=%s end_date=%s",
            request_id,
            type(exc).__name__,
            start_date,
            end_date,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=error_payload("Unable to generate this report right now.", "report_calculation_failed", request_id=request_id),
        ) from exc


@router.get("/inventory-valuation", response_model=InventoryValuationReport)
def inventory_valuation(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return ReportService(db).inventory_valuation(current_user)
