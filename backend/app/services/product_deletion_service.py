from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.config import get_settings
from app.core.exceptions import error_payload, not_found
from app.models.product import Product
from app.models.product_deletion_audit import ProductDeletionAudit
from app.models.product_inventory import ProductInventory
from app.models.product_variant import InventoryCostLot, ProductVariant
from app.models.product_barcode import ProductBarcode, ProductBarcodeAudit, ProductBarcodeVariantTarget
from app.models.product_update_audit import ProductUpdateAudit
from app.models.inventory_reconciliation import InventoryReconciliationAudit
from app.models.stock_import import StockImportRow
from app.models.stock_scan import StockScanSession, StockScanSessionItem
from app.models.stock_audit_event import StockAuditEvent
from app.models.purchase import Purchase
from app.models.purchase_item import PurchaseItem
from app.models.sale import Sale, SaleItem
from app.models.stock_history import StockHistory
from app.models.store import Store
from app.models.user import User
from app.services.file_service import FileService
from app.services.destructive_action_service import DestructiveActionService


class ProductDeletionService:
    """Owner-only destructive operations with a preflight-driven transaction."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def check(self, product_ids: list[UUID], current_user: User, request_id: str) -> dict:
        products = self._locked_products(product_ids, lock=False)
        self._ensure_all_found(product_ids, products)
        deletable: list[dict] = []
        blocked: list[dict] = []
        for product in products:
            assessment = self._assessment(product, current_user.store_id)
            if assessment["reason"]:
                blocked.append(self._blocked(product, assessment, request_id))
            else:
                deletable.append({
                    "product_id": str(product.id),
                    "product_name": product.name,
                    "classification": "ZERO_STOCK_INVENTORY_ONLY",
                    "references": assessment["references"],
                })
        return {"deletable": deletable, "blocked": blocked, "request_id": request_id}

    def permanently_delete(self, product_ids: list[UUID], confirmation: str, delete_password: str, idempotency_key: str, current_user: User, request_id: str, client_ip: str | None = None) -> dict:
        self._require_confirmation(confirmation, "DELETE", request_id)
        destructive = DestructiveActionService(self.db)
        cached = destructive._idempotent("PRODUCT_WRONG_ENTRY_DELETE", product_ids, idempotency_key, current_user, request_id)
        if cached:
            return {**cached, "already_completed": True}
        destructive._verify_password(delete_password, current_user, request_id, client_ip)

        products = self._locked_products(product_ids, lock=True)
        self._ensure_all_found(product_ids, products)
        blocked = [self._blocked(product, assessment, request_id) for product in products if (assessment := self._assessment(product, current_user.store_id))["reason"]]
        if blocked:
            self._audit_blocked(products, blocked, current_user, request_id)
            self.db.commit()
            self._conflict("Selected products cannot be permanently deleted.", "PRODUCT_HAS_TRANSACTION_HISTORY", request_id, blocked)

        image_paths = [product.image_url for product in products if product.image_url]
        try:
            deleted = []
            for product in products:
                counts = self._counts(product.id)
                self._audit(
                    product,
                    current_user,
                    request_id,
                    "PRODUCT_WRONG_ENTRY_PERMANENTLY_DELETED",
                    "WRONG_ENTRY_PURGE",
                    "Owner confirmed wrong-entry deletion",
                    counts,
                )
                self._purge_inventory_only_dependencies(product)
                deleted.append({"product_id": str(product.id), "product_name": product.name})
                self.db.delete(product)
            self.db.flush()
            result = {"deleted": deleted, "blocked": [], "request_id": request_id, "already_completed": False}
            destructive._audit("PRODUCT_WRONG_ENTRY_DELETE_COMPLETED", current_user, request_id, client_ip, "PRODUCT", record_counts={"deleted": len(deleted)})
            destructive._store_idempotent("PRODUCT_WRONG_ENTRY_DELETE", product_ids, idempotency_key, current_user, result)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        for path in image_paths:
            FileService(self.db).delete_product_image_path(path)
        return result

    def purge_test_data(self, product_ids: list[UUID], confirmation: str, reason: str, current_user: User, request_id: str) -> dict:
        self._require_confirmation(confirmation, "PURGE TEST DATA", request_id)
        store_id = self._store_id(current_user)
        store = self.db.get(Store, store_id)
        settings = get_settings()
        if not store or not (store.allow_test_data_purge or settings.app_env in {"development", "test"}):
            self._forbidden("Test-data purge is not enabled for this store.", "TEST_DATA_PURGE_DISABLED", request_id)

        products = self._locked_products(product_ids, lock=True)
        self._ensure_all_found(product_ids, products)
        blocked: list[dict] = []
        for product in products:
            assessment = self._assessment(product, store_id, allow_test_purge=True)
            if not product.is_test_data:
                assessment["reason"] = "This product is not explicitly marked as test data."
            counts = assessment["references"]
            if counts.get("purchase_items") or counts.get("sale_items"):
                assessment["reason"] = "This product is connected to a purchase or sale and cannot be purged without a parent test-data workflow."
            if assessment["reason"]:
                blocked.append(self._blocked(product, assessment, request_id))
        if blocked:
            self._audit_blocked(products, blocked, current_user, request_id)
            self.db.commit()
            self._conflict("Selected test products cannot be purged safely.", "TEST_DATA_PURGE_BLOCKED", request_id, blocked)

        image_paths = [product.image_url for product in products if product.image_url]
        try:
            deleted = []
            for product in products:
                counts = self._counts(product.id)
                self.db.query(StockHistory).filter(StockHistory.product_id == product.id).delete(synchronize_session=False)
                self.db.query(ProductInventory).filter(ProductInventory.product_id == product.id).delete(synchronize_session=False)
                self._audit(product, current_user, request_id, "PRODUCT_TEST_DATA_PURGED", "TEST_DATA_PURGE", reason, counts)
                deleted.append({"product_id": str(product.id), "product_name": product.name, "records_removed": counts})
                self.db.delete(product)
            self.db.flush()
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        for path in image_paths:
            FileService(self.db).delete_product_image_path(path)
        return {"deleted": deleted, "blocked": [], "request_id": request_id}

    def _locked_products(self, product_ids: Iterable[UUID], *, lock: bool) -> list[Product]:
        ids = list(dict.fromkeys(product_ids))
        query = self.db.query(Product).options(
            joinedload(Product.category),
            joinedload(Product.brand),
            selectinload(Product.variants),
        ).filter(Product.id.in_(ids))
        if lock:
            query = query.with_for_update()
        products = query.all()
        product_by_id = {product.id: product for product in products}
        return [product_by_id[product_id] for product_id in ids if product_id in product_by_id]

    @staticmethod
    def _ensure_all_found(requested: list[UUID], products: list[Product]) -> None:
        if len(set(requested)) != len(products):
            raise not_found("One or more selected products")

    def _assessment(self, product: Product, store_id: UUID | None, *, allow_test_purge: bool = False) -> dict:
        counts = self._counts(product.id)
        store_ids = self._reference_store_ids(product.id)
        if store_id is None:
            return {"reason": "Current user is not assigned to an active store.", "code": "STORE_SCOPE_REQUIRED", "references": counts}
        if product.store_id is None:
            return {"reason": "This legacy product has no store scope and cannot be permanently deleted until an owner assigns it to a store.", "code": "PRODUCT_STORE_SCOPE_MISSING", "references": counts}
        if product.store_id != store_id:
            return {"reason": "The selected product does not belong to the active store.", "code": "WRONG_STORE", "references": counts}
        if store_ids and (store_id not in store_ids or any(reference_store != store_id for reference_store in store_ids)):
            return {"reason": "The selected product does not belong exclusively to the active store.", "code": "WRONG_STORE", "references": counts}
        if counts["physical_stock"] > 0 and not allow_test_purge:
            return {"reason": f"{product.name} still has {counts['physical_stock']} units in stock. Correct stock, archive product, or view history.", "code": "PRODUCT_HAS_STOCK", "references": counts}
        if counts["active_cost_lot_pieces"] > 0 and not allow_test_purge:
            return {"reason": f"{product.name} still has {counts['active_cost_lot_pieces']} active cost-lot pieces. Correct stock, archive product, or view history.", "code": "PRODUCT_HAS_ACTIVE_COST_LOTS", "references": counts}
        if counts["sale_items"]:
            return {"reason": f"{product.name} has {counts['sale_items']} sale dependency record(s) and cannot be permanently deleted.", "code": "PRODUCT_HAS_SALE_DEPENDENCY", "references": counts}
        if counts["purchase_items"]:
            return {"reason": f"{product.name} has {counts['purchase_items']} purchase dependency record(s) and cannot be permanently deleted.", "code": "PRODUCT_HAS_PURCHASE_DEPENDENCY", "references": counts}
        if counts["protected_transactions"]:
            return {"reason": f"{product.name} has {counts['protected_transactions']} protected transaction reference(s) and cannot be permanently deleted.", "code": "PRODUCT_HAS_PROTECTED_TRANSACTION", "references": counts}
        return {"reason": None, "code": None, "references": counts}

    def _counts(self, product_id: UUID) -> dict[str, int]:
        variant_ids = [item[0] for item in self.db.query(ProductVariant.id).filter(ProductVariant.product_id == product_id).all()]
        inventory_stock = self.db.query(func.coalesce(func.sum(ProductInventory.current_stock), 0)).filter(ProductInventory.product_id == product_id).scalar() or 0
        product_stock = self.db.query(Product.current_stock).filter(Product.id == product_id).scalar() or 0
        variant_stock = self.db.query(func.coalesce(func.sum(ProductVariant.current_stock), 0)).filter(ProductVariant.product_id == product_id).scalar() or 0
        active_lot_pieces = 0
        if variant_ids:
            active_lot_pieces = self.db.query(func.coalesce(func.sum(InventoryCostLot.remaining_quantity), 0)).filter(
                InventoryCostLot.product_variant_id.in_(variant_ids),
                InventoryCostLot.remaining_quantity > 0,
            ).scalar() or 0
        protected_transactions = self.db.query(StockHistory).filter(
            StockHistory.product_id == product_id,
            or_(
                StockHistory.sale_id.isnot(None),
                StockHistory.purchase_id.isnot(None),
                StockHistory.sale_item_id.isnot(None),
                StockHistory.purchase_item_id.isnot(None),
            ),
        ).count()
        # A closed lot from a purchase is still commercial evidence, even after
        # its remaining quantity reaches zero.  A wrong-entry purge must never
        # remove it merely because the current stock is zero.
        if variant_ids:
            protected_transactions += self.db.query(InventoryCostLot).filter(
                InventoryCostLot.product_variant_id.in_(variant_ids),
                InventoryCostLot.purchase_id.isnot(None),
            ).count()
            # Scan items in a purchase-receiving session are also purchase
            # dependencies.  Other scan modes are inventory-only evidence and
            # are cleaned up atomically below.
            protected_transactions += self.db.query(StockScanSessionItem).join(StockScanSession).filter(
                StockScanSessionItem.product_variant_id.in_(variant_ids),
                StockScanSession.purchase_id.isnot(None),
            ).count()
        return {
            "inventory_transactions": self.db.query(StockHistory).filter(StockHistory.product_id == product_id).count(),
            "purchase_items": self.db.query(PurchaseItem).filter(or_(
                PurchaseItem.product_id == product_id,
                PurchaseItem.matched_product_id == product_id,
                PurchaseItem.product_variant_id.in_(variant_ids) if variant_ids else False,
            )).count(),
            "sale_items": self.db.query(SaleItem).filter(or_(
                SaleItem.product_id == product_id,
                SaleItem.product_variant_id.in_(variant_ids) if variant_ids else False,
            )).count(),
            "inventory_records": self.db.query(ProductInventory).filter(ProductInventory.product_id == product_id).count(),
            "variants": self.db.query(ProductVariant).filter(ProductVariant.product_id == product_id).count(),
            "variant_stock": int(variant_stock),
            "aggregate_product_stock": int(inventory_stock),
            "active_cost_lot_pieces": int(active_lot_pieces),
            "protected_transactions": protected_transactions,
            "physical_stock": max(int(product_stock), int(inventory_stock), int(variant_stock)),
        }

    def _purge_inventory_only_dependencies(self, product: Product) -> None:
        """Remove only product-scoped, zero-stock inventory evidence after preflight."""
        variant_ids = [variant.id for variant in product.variants]
        if variant_ids:
            # Preserve shared barcode registrations: remove this product's targets, and
            # re-home a mapping when another exact variant still uses it.
            mappings = self.db.query(ProductBarcode).filter(or_(ProductBarcode.product_id == product.id, ProductBarcode.product_variant_id.in_(variant_ids))).with_for_update().all()
            for mapping in mappings:
                self.db.query(ProductBarcodeVariantTarget).filter(ProductBarcodeVariantTarget.product_barcode_id == mapping.id, ProductBarcodeVariantTarget.product_variant_id.in_(variant_ids)).delete(synchronize_session=False)
                survivor = self.db.query(ProductBarcodeVariantTarget).filter(ProductBarcodeVariantTarget.product_barcode_id == mapping.id).first()
                if survivor:
                    variant = self.db.get(ProductVariant, survivor.product_variant_id)
                    if variant:
                        mapping.product_variant_id, mapping.product_id = variant.id, variant.product_id
                elif mapping.product_id == product.id or mapping.product_variant_id in variant_ids:
                    self.db.delete(mapping)
            # These are catalogue/inventory-only audit and barcode records.  The
            # complete, immutable deletion snapshot was written before cleanup.
            self.db.query(ProductBarcodeAudit).filter(or_(
                ProductBarcodeAudit.old_product_variant_id.in_(variant_ids),
                ProductBarcodeAudit.new_product_variant_id.in_(variant_ids),
            )).delete(synchronize_session=False)
            self.db.query(StockAuditEvent).filter(or_(StockAuditEvent.product_id == product.id, StockAuditEvent.product_variant_id.in_(variant_ids))).delete(synchronize_session=False)
            self.db.query(StockHistory).filter(StockHistory.product_id == product.id).delete(synchronize_session=False)
            self.db.query(StockScanSessionItem).filter(or_(
                StockScanSessionItem.product_id == product.id,
                StockScanSessionItem.product_variant_id.in_(variant_ids),
            )).delete(synchronize_session=False)
            self.db.query(StockImportRow).filter(or_(
                StockImportRow.product_id == product.id,
                StockImportRow.product_variant_id.in_(variant_ids),
            )).delete(synchronize_session=False)
            self.db.query(InventoryCostLot).filter(
                InventoryCostLot.product_variant_id.in_(variant_ids),
                InventoryCostLot.remaining_quantity <= 0,
                InventoryCostLot.purchase_id.is_(None),
            ).delete(synchronize_session=False)
        self.db.query(InventoryReconciliationAudit).filter(InventoryReconciliationAudit.product_id == product.id).delete(synchronize_session=False)
        self.db.query(ProductUpdateAudit).filter(ProductUpdateAudit.product_id == product.id).delete(synchronize_session=False)
        self.db.query(ProductInventory).filter(ProductInventory.product_id == product.id).delete(synchronize_session=False)

    def _reference_store_ids(self, product_id: UUID) -> set[UUID]:
        values: set[UUID] = set()
        values.update(value for (value,) in self.db.query(ProductInventory.store_id).filter(ProductInventory.product_id == product_id).all() if value)
        values.update(value for (value,) in self.db.query(StockHistory.store_id).filter(StockHistory.product_id == product_id).all() if value)
        values.update(value for (value,) in self.db.query(Purchase.store_id).join(PurchaseItem).filter(or_(PurchaseItem.product_id == product_id, PurchaseItem.matched_product_id == product_id)).all() if value)
        values.update(value for (value,) in self.db.query(Sale.store_id).join(SaleItem).filter(SaleItem.product_id == product_id).all() if value)
        return values

    def _blocked(self, product: Product, assessment: dict, request_id: str) -> dict:
        return {
            "product_id": str(product.id),
            "product_name": product.name,
            "reason": assessment["reason"],
            "code": assessment["code"],
            "references": assessment["references"],
            "request_id": request_id,
        }

    def _audit(self, product: Product, current_user: User, request_id: str, event_type: str, mode: str, reason: str | None, counts: dict) -> None:
        store_id = self._store_id(current_user)
        self.db.add(ProductDeletionAudit(
            store_id=store_id,
            product_id=product.id,
            event_type=event_type,
            delete_mode=mode,
            reason=reason,
            request_id=request_id,
            product_snapshot=self._deletion_snapshot(product),
            deleted_record_counts=counts,
            performed_by=current_user.id,
            performed_by_role=current_user.role.value,
        ))

    def _deletion_snapshot(self, product: Product) -> dict:
        """Capture the evidence needed to explain a later wrong-entry purge."""
        variant_ids = [variant.id for variant in product.variants]
        mappings = []
        if variant_ids:
            for mapping in self.db.query(ProductBarcode).filter(or_(
                ProductBarcode.product_id == product.id,
                ProductBarcode.product_variant_id.in_(variant_ids),
            )).all():
                targets = self.db.query(ProductBarcodeVariantTarget.product_variant_id).filter(
                    ProductBarcodeVariantTarget.product_barcode_id == mapping.id,
                ).all()
                mappings.append({
                    "id": str(mapping.id),
                    "barcode": mapping.barcode,
                    "barcode_type": mapping.barcode_type,
                    "manufacturer_barcode": mapping.manufacturer_barcode,
                    "primary_product_id": str(mapping.product_id),
                    "primary_variant_id": str(mapping.product_variant_id),
                    "target_variant_ids": [str(target_id) for (target_id,) in targets],
                })
        movements = self.db.query(
            StockHistory.movement_type,
            func.count(StockHistory.id),
            func.coalesce(func.sum(StockHistory.qty), 0),
        ).filter(StockHistory.product_id == product.id).group_by(StockHistory.movement_type).all()
        return {
            "id": str(product.id),
            "name": product.name,
            "sku": product.sku,
            "barcode": product.barcode,
            "category": product.category.name if product.category else None,
            "brand": product.brand.name if product.brand else None,
            "purchase_price": str(product.purchase_price),
            "selling_price": str(product.selling_price),
            "mrp": str(product.mrp) if product.mrp is not None else None,
            "variants": [{
                "id": str(variant.id),
                "color": variant.color,
                "size": variant.size,
                "sku": variant.internal_sku,
                "barcode": variant.barcode,
                "mrp": str(variant.mrp) if variant.mrp is not None else None,
                "selling_price": str(variant.selling_price),
                "purchase_cost": str(variant.last_purchase_cost),
            } for variant in product.variants],
            "barcode_mappings": mappings,
            "inventory_movement_summary": [{
                "movement_type": movement_type.value if hasattr(movement_type, "value") else str(movement_type),
                "count": count,
                "quantity_total": int(quantity_total),
            } for movement_type, count, quantity_total in movements],
            "is_test_data": product.is_test_data,
        }

    def _audit_blocked(self, products: list[Product], blocked: list[dict], current_user: User, request_id: str) -> None:
        blocked_by_id = {item["product_id"]: item for item in blocked}
        for product in products:
            item = blocked_by_id.get(str(product.id))
            if item:
                self._audit(product, current_user, request_id, "PRODUCT_DELETE_BLOCKED", "PERMANENT_DELETE", item["reason"], item["references"])

    def _completed_products_for_request(self, request_id: str, event_type: str) -> set[UUID]:
        return {product_id for (product_id,) in self.db.query(ProductDeletionAudit.product_id).filter(ProductDeletionAudit.request_id == request_id, ProductDeletionAudit.event_type == event_type).all()}

    @staticmethod
    def _store_id(current_user: User) -> UUID:
        if current_user.store_id is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_payload("Current user is not assigned to an active store.", "STORE_SCOPE_REQUIRED"))
        return current_user.store_id

    @staticmethod
    def _require_confirmation(value: str, expected: str, request_id: str) -> None:
        if value != expected:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={**error_payload(f"Type {expected} to confirm permanent deletion.", "DELETE_CONFIRMATION_REQUIRED"), "request_id": request_id})

    @staticmethod
    def _conflict(message: str, code: str, request_id: str, blocked: list[dict]) -> None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={**error_payload(message, code), "request_id": request_id, "blocked_products": blocked})

    @staticmethod
    def _forbidden(message: str, code: str, request_id: str) -> None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={**error_payload(message, code), "request_id": request_id})
