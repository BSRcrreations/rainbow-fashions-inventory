from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import require_owner
from app.database.session import get_db
from app.models.opening_stock_import import OpeningStockImportError, OpeningStockImportRow
from app.models.user import User
from app.schemas.opening_stock_import import (
    OpeningStockImportConfirm,
    OpeningStockImportDetail,
    OpeningStockImportErrorRead,
    OpeningStockImportRead,
    OpeningStockImportReverse,
    OpeningStockImportRowRead,
    OpeningStockImportReport,
)
from app.services.opening_stock_import_service import OpeningStockImportService


router = APIRouter(prefix="/opening-stock-imports", tags=["Opening stock imports"])


def _detail(service: OpeningStockImportService, import_id: UUID, current_user: User) -> OpeningStockImportDetail:
    batch = service.get(import_id, current_user)
    rows, errors = service.detail_rows(import_id)
    by_row: dict[int, list[OpeningStockImportErrorRead]] = {}
    for error in errors:
        item = OpeningStockImportErrorRead(row_number=error.row_number, field=error.field, code=error.code, message=error.message)
        if error.row_number is not None:
            by_row.setdefault(error.row_number, []).append(item)
    return OpeningStockImportDetail(
        **OpeningStockImportRead.model_validate(batch).model_dump(),
        rows=[OpeningStockImportRowRead(row_number=row.row_number, validation_status=row.validation_status, normalized_data=row.normalized_data, errors=by_row.get(row.row_number, [])) for row in rows],
        errors=[OpeningStockImportErrorRead(row_number=error.row_number, field=error.field, code=error.code, message=error.message) for error in errors if error.row_number is None],
    )


@router.post("/upload", response_model=OpeningStockImportRead, status_code=201)
async def upload_opening_stock(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_owner),
):
    return await OpeningStockImportService(db).upload_and_validate(file, current_user, request.state.request_id)


@router.get("", response_model=list[OpeningStockImportRead])
def list_opening_stock_imports(db: Session = Depends(get_db), current_user: User = Depends(require_owner)):
    return OpeningStockImportService(db).list(current_user)


@router.get("/{import_id}", response_model=OpeningStockImportDetail)
def opening_stock_import_detail(import_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_owner)):
    return _detail(OpeningStockImportService(db), import_id, current_user)


@router.post("/{import_id}/confirm", response_model=OpeningStockImportReport)
def confirm_opening_stock_import(import_id: UUID, payload: OpeningStockImportConfirm, request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_owner)):
    return OpeningStockImportService(db).confirm(import_id, payload, current_user, request.state.request_id)


@router.post("/{import_id}/reverse", response_model=OpeningStockImportReport)
def reverse_opening_stock_import(import_id: UUID, payload: OpeningStockImportReverse, request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_owner)):
    return OpeningStockImportService(db).reverse(import_id, payload, current_user, request.state.request_id)
