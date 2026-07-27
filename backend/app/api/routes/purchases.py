from __future__ import annotations

from uuid import UUID

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.purchase import (
    PurchaseCancelRequest,
    PurchaseDetailRead,
    PurchaseFromDocumentCreate,
    PurchaseItemPatch,
    PurchaseItemReview,
    PurchasePatch,
    PurchaseRead,
    PurchaseReviewUpdate,
    PurchaseUploadResponse,
    PurchaseValidationRead,
)
from app.services.purchase_service import PurchaseService


router = APIRouter(prefix="/purchases", tags=["Purchases"])


@router.get("", response_model=list[PurchaseRead])
def list_purchases(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list:
    return PurchaseService(db).list(current_user, skip, limit)


@router.post("/upload", response_model=PurchaseUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PurchaseUploadResponse:
    return await PurchaseService(db).upload_invoice(file, current_user)


@router.post("/from-document", response_model=PurchaseUploadResponse, status_code=status.HTTP_201_CREATED)
def create_purchase_from_document(payload: PurchaseFromDocumentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> PurchaseUploadResponse:
    return PurchaseService(db).create_from_document(payload.job_id, current_user)


@router.get("/{purchase_id}", response_model=PurchaseDetailRead)
def get_purchase(purchase_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> PurchaseDetailRead:
    return PurchaseService(db).detail(purchase_id, current_user)


@router.get("/{purchase_id}/document")
def get_purchase_document(purchase_id: UUID, download: bool = False, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> FileResponse:
    uploaded = PurchaseService(db).invoice_file(purchase_id, current_user)
    return FileResponse(
        path=Path(uploaded.storage_path),
        media_type=uploaded.content_type,
        filename=uploaded.original_filename if download else None,
        content_disposition_type="attachment" if download else "inline",
    )


@router.patch("/{purchase_id}", response_model=PurchaseRead)
def patch_purchase(purchase_id: UUID, payload: PurchasePatch, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> PurchaseRead:
    return PurchaseService(db).patch(purchase_id, payload, current_user)


@router.post("/{purchase_id}/validate", response_model=PurchaseValidationRead)
def validate_purchase(purchase_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> PurchaseValidationRead:
    return PurchaseService(db).validate(purchase_id, current_user)


@router.post("/{purchase_id}/cancel", response_model=PurchaseRead)
def cancel_purchase(purchase_id: UUID, payload: PurchaseCancelRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> PurchaseRead:
    return PurchaseService(db).cancel(purchase_id, payload.reason, payload.version, current_user)


@router.post("/{purchase_id}/items", response_model=PurchaseRead)
def add_purchase_item(purchase_id: UUID, payload: PurchaseItemReview, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> PurchaseRead:
    return PurchaseService(db).add_item(purchase_id, payload, current_user)


@router.patch("/{purchase_id}/items/{item_id}", response_model=PurchaseRead)
def patch_purchase_item(purchase_id: UUID, item_id: UUID, payload: PurchaseItemPatch, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> PurchaseRead:
    return PurchaseService(db).patch_item(purchase_id, item_id, payload, current_user)


@router.delete("/{purchase_id}/items/{item_id}", response_model=PurchaseRead)
def delete_purchase_item(purchase_id: UUID, item_id: UUID, version: Optional[int] = Query(default=None), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> PurchaseRead:
    return PurchaseService(db).delete_item(purchase_id, item_id, version, current_user)


@router.put("/{purchase_id}/review", response_model=PurchaseRead)
def update_purchase_review(
    purchase_id: UUID,
    payload: PurchaseReviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchaseService(db).update_review(purchase_id, payload, current_user)


@router.post("/{purchase_id}/confirm", response_model=PurchaseRead)
def confirm_purchase(
    purchase_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchaseService(db).confirm(purchase_id, current_user)
