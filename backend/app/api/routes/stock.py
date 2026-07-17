from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_manager_or_owner
from app.database.session import get_db
from app.models.user import User
from datetime import datetime
from typing import Optional

from app.schemas.stock import StockAdjustmentCreate, StockHistoryRead, StockSaleCreate
from app.services.stock_service import StockService


router = APIRouter(prefix="/stock", tags=["Stock"])


@router.get("/history", response_model=list[StockHistoryRead])
def stock_history(
    skip: int = 0,
    limit: int = 100,
    movement_type: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list:
    return StockService(db).history(skip, limit, movement_type=movement_type, from_date=from_date, to_date=to_date)


@router.post("/adjustments", response_model=StockHistoryRead, status_code=status.HTTP_201_CREATED)
def adjust_stock(payload: StockAdjustmentCreate, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    return StockService(db).adjust(payload, current_user)


@router.post("/sales", response_model=StockHistoryRead, status_code=status.HTTP_201_CREATED)
def record_sale(payload: StockSaleCreate, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    return StockService(db).sell(payload, current_user)
