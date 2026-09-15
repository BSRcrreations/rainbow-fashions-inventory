from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_report_reader
from app.database.session import get_db
from app.models.user import User
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard_service import DashboardService


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> DashboardSummary:
    return DashboardService(db).summary(current_user)


@router.get("/shop-summary")
def shop_summary_cards(db: Session = Depends(get_db), current_user: User = Depends(require_report_reader)):
    from app.services.shop_summary_service import shop_summary
    return shop_summary(db, current_user)
