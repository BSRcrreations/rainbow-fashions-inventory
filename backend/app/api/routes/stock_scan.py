from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_manager_or_owner, require_owner
from app.database.session import get_db
from app.models.user import User
from app.schemas.stock_scan import (
    BarcodeAssignment,
    BarcodeTransferRequest,
    BarcodeImageResolutionRead,
    BarcodeOnboarding,
    BarcodeProductOnboarding,
    ProductVariantBarcodeRead,
    StockScanConfirmRequest,
    StockScanItemUpdate,
    StockScanRequest,
    StockScanSessionCreate,
    StockScanSessionRead,
    StockScanSessionUpdate,
    StockScanValidationRead,
)
from app.schemas.stock import StockHistoryRead
from app.services.stock_scan_service import StockScanService


router = APIRouter(prefix="/stock-scan", tags=["Stock scan"])
variants_router = APIRouter(prefix="/product-variants", tags=["Product variants"])
barcodes_router = APIRouter(prefix="/barcodes", tags=["Barcodes"])


@variants_router.get("/by-barcode/{barcode}", response_model=ProductVariantBarcodeRead)
def variant_by_barcode(barcode: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> ProductVariantBarcodeRead:
    return StockScanService(db).resolve_barcode(barcode, current_user)


@variants_router.post("/{variant_id}/barcode", response_model=ProductVariantBarcodeRead)
def assign_variant_barcode(variant_id: UUID, payload: BarcodeAssignment, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)) -> ProductVariantBarcodeRead:
    return StockScanService(db).assign_barcode(variant_id, payload, current_user)


@variants_router.post("/{variant_id}/barcodes", response_model=ProductVariantBarcodeRead)
def add_variant_barcode(variant_id: UUID, payload: BarcodeOnboarding, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)) -> ProductVariantBarcodeRead:
    if payload.product_variant_id != variant_id:
        payload.product_variant_id = variant_id
    return StockScanService(db).onboard_barcode(payload, current_user)


@barcodes_router.post("/onboard", response_model=ProductVariantBarcodeRead)
def onboard_barcode(payload: BarcodeOnboarding, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)) -> ProductVariantBarcodeRead:
    return StockScanService(db).onboard_barcode(payload, current_user)


@barcodes_router.delete("/{barcode_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_barcode(barcode_id: UUID, request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)) -> Response:
    StockScanService(db).remove_barcode(barcode_id, current_user, request.state.request_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@barcodes_router.post("/{barcode_id}/transfer", response_model=ProductVariantBarcodeRead)
def transfer_barcode(barcode_id: UUID, payload: BarcodeTransferRequest, request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_owner)) -> ProductVariantBarcodeRead:
    if not payload.confirm_transfer:
        from app.core.exceptions import bad_request
        raise bad_request("Confirm the barcode transfer before continuing", "BARCODE_TRANSFER_CONFIRMATION_REQUIRED")
    return StockScanService(db).transfer_barcode(barcode_id, payload.target_variant_id, current_user, request.state.request_id)


@barcodes_router.post("/resolve-image", response_model=BarcodeImageResolutionRead)
async def resolve_barcode_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_owner),
) -> BarcodeImageResolutionRead:
    return await StockScanService(db).resolve_label_image(file, current_user)


@barcodes_router.post("/onboard-product", response_model=StockScanSessionRead)
def onboard_product(
    payload: BarcodeProductOnboarding,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager_or_owner),
) -> StockScanSessionRead:
    return StockScanService(db).onboard_product(payload, current_user, request.state.request_id)


@router.post("/sessions", response_model=StockScanSessionRead, status_code=status.HTTP_201_CREATED)
def create_session(payload: StockScanSessionCreate, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)) -> StockScanSessionRead:
    return StockScanService(db).create_session(payload, current_user)


@router.get("/sessions/{session_id}", response_model=StockScanSessionRead)
def get_session(session_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> StockScanSessionRead:
    return StockScanService(db).get_session(session_id, current_user)


@router.patch("/sessions/{session_id}", response_model=StockScanSessionRead)
def update_session(session_id: UUID, payload: StockScanSessionUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)) -> StockScanSessionRead:
    return StockScanService(db).update_session(session_id, payload, current_user)


@router.post("/sessions/{session_id}/scan", response_model=StockScanSessionRead)
def scan_barcode(session_id: UUID, payload: StockScanRequest, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)) -> StockScanSessionRead:
    return StockScanService(db).scan(session_id, payload, current_user)


@router.patch("/sessions/{session_id}/items/{item_id}", response_model=StockScanSessionRead)
def update_scan_item(session_id: UUID, item_id: UUID, payload: StockScanItemUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)) -> StockScanSessionRead:
    return StockScanService(db).update_item(session_id, item_id, payload, current_user)


@router.delete("/sessions/{session_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scan_item(session_id: UUID, item_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)) -> Response:
    StockScanService(db).delete_item(session_id, item_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scan_session(session_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)) -> Response:
    StockScanService(db).delete_session(session_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/sessions/{session_id}/items/{item_id}/correction-target", response_model=StockHistoryRead)
def scan_item_correction_target(session_id: UUID, item_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)) -> StockHistoryRead:
    return StockScanService(db).correction_target(session_id, item_id, current_user)


@router.post("/sessions/{session_id}/validate", response_model=StockScanValidationRead)
def validate_session(session_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)) -> StockScanValidationRead:
    valid, messages, session = StockScanService(db).validate(session_id, current_user)
    return StockScanValidationRead(valid=valid, messages=messages, session=session)


@router.post("/sessions/{session_id}/confirm", response_model=StockScanSessionRead)
def confirm_session(session_id: UUID, payload: StockScanConfirmRequest, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)) -> StockScanSessionRead:
    return StockScanService(db).confirm(session_id, payload, current_user)


@router.post("/sessions/{session_id}/cancel", response_model=StockScanSessionRead)
def cancel_session(session_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(require_manager_or_owner)) -> StockScanSessionRead:
    return StockScanService(db).cancel(session_id, current_user)
