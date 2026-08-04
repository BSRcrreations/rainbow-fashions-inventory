from __future__ import annotations

import csv
from io import StringIO
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import require_manager_or_owner, require_owner
from app.database.session import get_db
from app.models.user import User
from app.schemas.inventory_reconciliation import ReconciliationItem, ReconciliationRepairPreview, ReconciliationRepairRequest, ReconciliationRepairResult, ReconciliationSummary
from app.services.inventory_reconciliation_service import InventoryReconciliationService


router = APIRouter(prefix="/inventory/reconciliation", tags=["Inventory reconciliation"])


@router.get("", response_model=list[ReconciliationItem])
def reconciliation(db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    return InventoryReconciliationService(db).report(current_user)


@router.get("/summary", response_model=ReconciliationSummary)
def reconciliation_summary(db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    return InventoryReconciliationService(db).summary(current_user)


@router.get("/export")
def export_reconciliation(db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    rows = InventoryReconciliationService(db).report(current_user)
    output = StringIO(); writer = csv.writer(output)
    writer.writerow(["product_id", "variant_id", "category", "severity", "variant_stock", "product_stock", "product_inventory_stock", "cost_lot_quantity", "expected_product_stock", "difference", "repair_eligible"])
    for row in rows:
        writer.writerow([row.product_id, row.variant_id or "", row.category, row.severity, row.variant_stock, row.product_stock, row.product_inventory_stock if row.product_inventory_stock is not None else "", row.remaining_cost_lot_quantity, row.expected_product_stock, row.difference, row.repair_eligible])
    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=inventory-reconciliation.csv"})


@router.get("/{product_id}", response_model=list[ReconciliationItem])
def product_reconciliation(product_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    return InventoryReconciliationService(db).report(current_user, product_id)


@router.post("/repair-preview", response_model=ReconciliationRepairPreview)
def repair_preview(payload: ReconciliationRepairRequest, db: Session = Depends(get_db), current_user: User = Depends(require_owner)):
    return InventoryReconciliationService(db).repair_preview(payload, current_user)


@router.post("/repair", response_model=ReconciliationRepairResult)
def repair(payload: ReconciliationRepairRequest, request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_owner)):
    return InventoryReconciliationService(db).repair(payload, current_user, request.state.request_id)
