from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Header, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import require_manager_or_owner
from app.database.session import get_db
from app.models.user import User
from app.schemas.stock_import import StockImportPreview, StockImportRead
from app.services.stock_import_service import StockImportService


router = APIRouter(prefix="/stock-imports", tags=["Stock imports"])


@router.post("/opening-stock/upload", response_model=StockImportRead, status_code=status.HTTP_201_CREATED)
async def upload_opening_stock(
    request: Request,
    file: UploadFile = File(...),
    idempotency_key: str = Header(default="", alias="Idempotency-Key"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_owner),
):
    content = await file.read()
    return StockImportService(db).upload_opening_stock(content, file.filename or "opening-stock.csv", idempotency_key, current_user, request.state.request_id)


@router.get("", response_model=list[StockImportRead])
def list_stock_imports(db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    return StockImportService(db).list(current_user)


@router.get("/{import_id}", response_model=StockImportRead)
def get_stock_import(import_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    return StockImportService(db).get(import_id, current_user)


@router.get("/{import_id}/preview", response_model=StockImportPreview)
def preview_stock_import(import_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    stock_import, rows = StockImportService(db).preview(import_id, current_user)
    return StockImportPreview.model_validate(stock_import).model_copy(update={"rows": rows})


@router.post("/{import_id}/confirm", response_model=StockImportRead)
def confirm_stock_import(import_id: UUID, request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)):
    return StockImportService(db).confirm(import_id, current_user, request.state.request_id)
