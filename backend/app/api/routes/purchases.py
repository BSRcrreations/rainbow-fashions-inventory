from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.purchase import PurchaseRead, PurchaseReviewUpdate, PurchaseUploadResponse
from app.services.purchase_service import PurchaseService


router = APIRouter(prefix="/purchases", tags=["Purchases"])


@router.get("", response_model=list[PurchaseRead])
def list_purchases(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list:
    return PurchaseService(db).list(skip, limit)


@router.post("/upload", response_model=PurchaseUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PurchaseUploadResponse:
    return await PurchaseService(db).upload_invoice(file, current_user)


@router.get("/{purchase_id}", response_model=PurchaseRead)
def get_purchase(purchase_id: UUID, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return PurchaseService(db).get(purchase_id)


@router.put("/{purchase_id}/review", response_model=PurchaseRead)
def update_purchase_review(
    purchase_id: UUID,
    payload: PurchaseReviewUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return PurchaseService(db).update_review(purchase_id, payload)


@router.post("/{purchase_id}/confirm", response_model=PurchaseRead)
def confirm_purchase(
    purchase_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PurchaseService(db).confirm(purchase_id, current_user)
