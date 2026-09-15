from __future__ import annotations

from datetime import date
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import require_report_reader
from app.core.exceptions import error_payload
from app.database.session import get_db
from app.models.user import User
from app.schemas.report import BusinessReportsSummary, InventoryValuationReport
from app.services.report_service import ReportService


router = APIRouter(prefix="/reports", tags=["Reports"])
logger = logging.getLogger(__name__)


@router.get("/summary", response_model=BusinessReportsSummary)
def reports_summary(request: Request, start_date: Optional[date] = None, end_date: Optional[date] = None, db: Session = Depends(get_db), current_user: User = Depends(require_report_reader)):
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
def inventory_valuation(db: Session = Depends(get_db), current_user: User = Depends(require_report_reader)):
    return ReportService(db).inventory_valuation(current_user)


@router.get("/export.xlsx")
def export_business_workbook(start_date: date, end_date: date, db: Session = Depends(get_db), current_user: User = Depends(require_report_reader)):
    from fastapi import Response
    from app.services.report_export_service import ReportExportService
    return Response(ReportExportService(db).workbook(current_user,start_date,end_date), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition":"attachment; filename=rainbow-business-reports.xlsx"})


@router.get("/low-stock")
def low_stock_report(page: int = 1, category_id: Optional[str] = None, brand_id: Optional[str] = None, supplier_id: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(require_report_reader)):
    from uuid import UUID
    from app.core.exceptions import bad_request
    from app.services.report_export_service import ReportExportService
    try:
        ids = [UUID(value) if value else None for value in (category_id,brand_id,supplier_id)]
    except ValueError:
        raise bad_request("Choose a valid category, brand or supplier.")
    if page<1: raise bad_request("Choose a valid page.")
    return ReportExportService(db).low_stock(current_user,page,*ids)
