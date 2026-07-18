from __future__ import annotations

from datetime import date
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.sale import SaleCreate, SaleListResponse, SaleRead, SalesDashboardResponse
from app.services.sale_service import SaleService


router = APIRouter(prefix="/sales", tags=["Sales"])


@router.get("/dashboard", response_model=SalesDashboardResponse)
def sales_dashboard(
    preset: Literal["today", "yesterday", "week", "month", "custom"] = "today",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return SaleService(db).dashboard(preset, start_date, end_date)


@router.get("/export")
def export_sales(
    format: Literal["xlsx", "pdf"] = Query("xlsx"),
    search: Optional[str] = None,
    payment_mode: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    invoice_number: Optional[str] = None,
    customer_name: Optional[str] = None,
    cashier_name: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> Response:
    service = SaleService(db)
    records = service.export_records(search, payment_mode, start_date, end_date, invoice_number, customer_name, cashier_name)
    if format == "pdf":
        return Response(
            content=service.export_pdf(records),
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="sales-history.pdf"'},
        )
    return Response(
        content=service.export_xlsx(records),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="sales-history.xlsx"'},
    )


@router.get("", response_model=SaleListResponse)
def list_sales(
    page: int = 1,
    page_size: int = 25,
    search: Optional[str] = None,
    payment_mode: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    invoice_number: Optional[str] = None,
    customer_name: Optional[str] = None,
    cashier_name: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return SaleService(db).list_paginated(page, page_size, search, payment_mode, start_date, end_date, invoice_number, customer_name, cashier_name)


@router.post("", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
def create_sale(payload: SaleCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return SaleService(db).create(payload, current_user)


@router.get("/{sale_id}", response_model=SaleRead)
def get_sale(sale_id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return SaleService(db).get(sale_id)
