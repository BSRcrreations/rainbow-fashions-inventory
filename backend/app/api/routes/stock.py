from __future__ import annotations

import csv
from io import StringIO
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_manager_or_owner
from app.database.session import get_db
from app.models.enums import StockMovementType
from app.models.user import User
from app.schemas.stock import StockAdjustmentCreate, StockHistoryRead
from app.services.stock_service import StockService


router = APIRouter(prefix="/stock", tags=["Stock"])


@router.get("/history/export")
def export_stock_history(
    product_id: Optional[UUID] = None,
    movement_type: Optional[StockMovementType] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    movements = StockService(db).history(0, 10000, product_id, movement_type, current_user.store_id)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Product", "Type", "Quantity", "Before", "After", "Reference", "User", "Date"])
    for movement in movements:
        writer.writerow([
            movement.product.name if movement.product else str(movement.product_id),
            movement.movement_type.value.replace("_", " ").title(),
            movement.qty,
            movement.before_stock,
            movement.after_stock,
            movement.reference or "",
            movement.created_by_user.full_name if movement.created_by_user else "System",
            movement.movement_date.isoformat(),
        ])
    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="inventory-movements.csv"'})


@router.get("/history", response_model=list[StockHistoryRead])
def stock_history(
    skip: int = 0,
    limit: int = 100,
    product_id: Optional[UUID] = None,
    movement_type: Optional[StockMovementType] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    return StockService(db).history(
        skip,
        limit,
        product_id,
        movement_type,
        current_user.store_id,
        from_date,
        to_date,
    )


@router.post("/adjustments", response_model=StockHistoryRead, status_code=status.HTTP_201_CREATED)
def adjust_stock(payload: StockAdjustmentCreate, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    return StockService(db).adjust(payload, current_user)
