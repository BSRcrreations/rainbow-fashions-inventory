from __future__ import annotations

from datetime import date
from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_manager_or_owner, require_owner
from app.database.session import get_db
from app.models.user import User
from app.schemas.sale import SaleAuditRead, SaleCatalogProduct, SaleCatalogVariant, SaleCreate, SaleDeleteCheckRequest, SaleDeleteRequest, SaleListResponse, SaleRead, SaleReturnCreate, SaleReturnRead, SaleUpdate, SaleVoidRequest, SalesDashboardResponse
from app.services.destructive_action_service import DestructiveActionService
from app.services.sale_service import SaleService


router = APIRouter(prefix="/sales", tags=["Sales"])


@router.post("/delete-check")
def check_sale_delete(payload: SaleDeleteCheckRequest, request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_owner)):
    return DestructiveActionService(db).check_sales(payload.sale_ids, current_user, request.state.request_id)


@router.post("/delete")
def delete_sales(payload: SaleDeleteRequest, request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_owner)):
    return DestructiveActionService(db).delete_sales(payload.sale_ids, payload.delete_password, request.headers.get("Idempotency-Key", ""), current_user, request.state.request_id, request.client.host if request.client else None)


@router.get("/dashboard", response_model=SalesDashboardResponse)
def sales_dashboard(
    preset: Literal["today", "yesterday", "week", "month", "custom"] = "today",
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return SaleService(db).dashboard(preset, start_date, end_date, current_user)


@router.get("/catalog", response_model=list[SaleCatalogProduct])
def sale_catalog(search: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return SaleService(db).catalog(search, current_user)


@router.get("/catalog/barcode/{barcode}", response_model=SaleCatalogVariant)
def sale_catalog_barcode(barcode: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return SaleService(db).variant_by_barcode(barcode, current_user)


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
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    service = SaleService(db)
    records = service.export_records(search, payment_mode, start_date, end_date, invoice_number, customer_name, cashier_name, status_filter, current_user=current_user)
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
    status_filter: Optional[str] = None,
    sort: Literal["newest", "oldest", "total"] = "newest",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return SaleService(db).list_paginated(page, page_size, search, payment_mode, start_date, end_date, invoice_number, customer_name, cashier_name, status_filter, current_user, sort)


@router.post("", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
def create_sale(payload: SaleCreate, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return SaleService(db).create(payload, current_user, request.state.request_id)


@router.get("/{sale_id}", response_model=SaleRead)
def get_sale(sale_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return SaleService(db).get(sale_id, current_user)


@router.patch("/{sale_id}", response_model=SaleRead)
def update_sale(sale_id: UUID, payload: SaleUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    return SaleService(db).update(sale_id, payload, current_user)


@router.post("/{sale_id}/void", response_model=SaleRead)
def void_sale(sale_id: UUID, payload: SaleVoidRequest, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    return SaleService(db).void(sale_id, payload, current_user)


@router.post("/{sale_id}/returns", response_model=SaleReturnRead, status_code=status.HTTP_201_CREATED)
def create_sale_return(sale_id: UUID, payload: SaleReturnCreate, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    return SaleService(db).create_return(sale_id, payload, current_user)


@router.get("/{sale_id}/returns", response_model=list[SaleReturnRead])
def list_sale_returns(sale_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    return SaleService(db).list_returns(sale_id, current_user)


@router.get("/{sale_id}/audit", response_model=list[SaleAuditRead])
def list_sale_audits(sale_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    return SaleService(db).list_audits(sale_id, current_user)
