from __future__ import annotations

"""Safe removal of barcode registration records without deleting business history."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import bad_request
from app.models.enums import PurchaseStatus, SaleStatus, StockScanStatus
from app.models.product import Product
from app.models.product_barcode import ProductBarcode, ProductBarcodeAudit, ProductBarcodeVariantTarget
from app.models.product_variant import ProductVariant
from app.models.purchase import Purchase
from app.models.purchase_item import PurchaseItem
from app.models.sale import Sale, SaleItem
from app.models.stock_scan import StockScanSession, StockScanSessionItem
from app.models.user import User
from app.schemas.stock_scan import BarcodeDeletionCheckRead


class BarcodeDeletionService:
    """Preflight and atomically purge non-historical barcode ownership records."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def check(self, barcode: str, current_user: User) -> BarcodeDeletionCheckRead:
        return self._assessment(self._normalise(barcode), self._store_id(current_user))

    def permanently_delete(self, barcode: str, confirmation: str, current_user: User) -> dict:
        if confirmation != "DELETE BARCODE":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={
                "message": "Type DELETE BARCODE to confirm permanent deletion.",
                "code": "DELETE_CONFIRMATION_REQUIRED",
            })
        normalized = self._normalise(barcode)
        store_id = self._store_id(current_user)
        try:
            assessment = self._assessment(normalized, store_id, lock=True)
            if not assessment.can_permanently_delete:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={
                    "message": assessment.reason or "This barcode cannot be permanently deleted.",
                    "code": "BARCODE_DELETE_BLOCKED",
                    "historical_references": assessment.historical_references,
                    "active_assignments": assessment.active_assignments,
                })

            mappings = self.db.query(ProductBarcode).filter(
                ProductBarcode.store_id == store_id,
                func.lower(ProductBarcode.barcode) == normalized.casefold(),
            ).with_for_update().all()
            mapping_ids = [mapping.id for mapping in mappings]
            if mapping_ids:
                self.db.query(ProductBarcodeVariantTarget).filter(
                    ProductBarcodeVariantTarget.product_barcode_id.in_(mapping_ids)
                ).delete(synchronize_session=False)
                self.db.query(ProductBarcode).filter(ProductBarcode.id.in_(mapping_ids)).delete(synchronize_session=False)

            # Legacy columns are current configuration, not transaction history.
            # They are replaced with an internal non-scannable placeholder because
            # product_variants.barcode is non-null and unique by schema design.
            variants = self.db.query(ProductVariant).filter(
                ProductVariant.store_id == store_id,
                func.lower(ProductVariant.barcode) == normalized.casefold(),
            ).with_for_update().all()
            for variant in variants:
                variant.barcode = self._unassigned_value(variant.id)
            self.db.query(Product).filter(
                Product.store_id == store_id,
                func.lower(Product.barcode) == normalized.casefold(),
            ).update({Product.barcode: None}, synchronize_session=False)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return {"barcode": normalized, "deleted": True, "status": "AVAILABLE"}

    def _assessment(self, barcode: str, store_id: UUID, *, lock: bool = False) -> BarcodeDeletionCheckRead:
        mappings_query = self.db.query(ProductBarcode).filter(
            ProductBarcode.store_id == store_id,
            func.lower(ProductBarcode.barcode) == barcode.casefold(),
        )
        if lock:
            mappings_query = mappings_query.with_for_update()
        mappings = mappings_query.all()
        active_assignments = sum(1 for mapping in mappings if mapping.active)
        legacy_assignments = self.db.query(ProductVariant).filter(
            ProductVariant.store_id == store_id,
            func.lower(ProductVariant.barcode) == barcode.casefold(),
        ).count()
        # A raw legacy value with no map is itself a current assignment.
        if not mappings:
            active_assignments += legacy_assignments
        confirmed_sales = self.db.query(SaleItem).join(Sale).filter(
            Sale.store_id == store_id,
            Sale.status.in_([SaleStatus.COMPLETED, SaleStatus.EDITED, SaleStatus.PARTIALLY_RETURNED, SaleStatus.RETURNED]),
            func.lower(SaleItem.barcode_snapshot) == barcode.casefold(),
        ).count()
        confirmed_purchases = self.db.query(PurchaseItem).join(Purchase).filter(
            Purchase.store_id == store_id,
            Purchase.status == PurchaseStatus.CONFIRMED,
            func.lower(PurchaseItem.barcode) == barcode.casefold(),
        ).count()
        confirmed_stock = self.db.query(StockScanSessionItem).join(StockScanSession).filter(
            StockScanSession.store_id == store_id,
            StockScanSession.status == StockScanStatus.CONFIRMED,
            func.lower(StockScanSessionItem.barcode) == barcode.casefold(),
        ).count()
        draft_references = self.db.query(StockScanSessionItem).join(StockScanSession).filter(
            StockScanSession.store_id == store_id,
            StockScanSession.status.in_([StockScanStatus.DRAFT, StockScanStatus.IN_PROGRESS, StockScanStatus.REVIEW_REQUIRED]),
            func.lower(StockScanSessionItem.barcode) == barcode.casefold(),
        ).count()
        audit_references = self.db.query(ProductBarcodeAudit).filter(
            ProductBarcodeAudit.store_id == store_id,
            func.lower(ProductBarcodeAudit.barcode) == barcode.casefold(),
        ).count()
        historical = confirmed_sales + confirmed_purchases + confirmed_stock
        reason = None
        if active_assignments:
            reason = "Remove the current barcode assignment before permanently deleting its registration records."
        elif historical:
            reason = "Historical sales, purchases, or confirmed stock records were found and will be preserved."
        elif draft_references:
            reason = "Remove this barcode from unconfirmed stock drafts before permanently deleting it."
        return BarcodeDeletionCheckRead(
            barcode=barcode, active_assignments=active_assignments, historical_references=historical,
            draft_references=draft_references, audit_references=audit_references,
            can_permanently_delete=reason is None, reason=reason,
        )

    @staticmethod
    def _normalise(barcode: str) -> str:
        value = barcode.strip()
        if not value:
            raise bad_request("Barcode is required")
        return value

    @staticmethod
    def _store_id(current_user: User) -> UUID:
        if not current_user.store_id:
            raise bad_request("Current user is not assigned to an active store.", "STORE_SCOPE_REQUIRED")
        return current_user.store_id

    @staticmethod
    def _unassigned_value(variant_id: UUID) -> str:
        return f"UNASSIGNED-{variant_id.hex}"
