from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Iterable
from uuid import UUID

from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.exceptions import bad_request, conflict, not_found
from app.models.destructive_action import DestructiveIdempotencyRecord
from app.models.inventory_reconciliation import InventoryReconciliationAudit
from app.models.product import Product
from app.models.product_inventory import ProductInventory
from app.models.product_barcode import ProductBarcode
from app.models.product_variant import ProductVariant
from app.models.stock_history import StockHistory
from app.models.user import User
from app.schemas.inventory_reconciliation import ReconciliationItem, ReconciliationRepairPreview, ReconciliationRepairRequest, ReconciliationRepairResult, ReconciliationSummary
from app.services.backup_status_service import BackupStatusService


REPAIR_CONFIRMATION = "REPAIR INVENTORY AGGREGATES"


class InventoryReconciliationService:
    """Read-only integrity report; repair only derives legacy aggregates from variants."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    def report(self, current_user: User, product_id: UUID | None = None) -> list[ReconciliationItem]:
        store_id = self._store_id(current_user)
        query = self.db.query(Product).options(selectinload(Product.variants).selectinload(ProductVariant.cost_lots), selectinload(Product.inventory_items)).filter(Product.store_id == store_id)
        if product_id:
            query = query.filter(Product.id == product_id)
        products = query.order_by(Product.name).all()
        if product_id and not products:
            raise not_found("Product")
        variant_ids = [variant.id for product in products for variant in product.variants]
        barcode_conflicts: set[UUID] = set()
        latest_history: dict[UUID, int] = {}
        if variant_ids:
            barcode_conflicts = {row.product_variant_id for row in self.db.query(ProductBarcode).join(ProductVariant, ProductBarcode.product_variant_id == ProductVariant.id).filter(ProductBarcode.store_id == store_id, ProductVariant.product_id != ProductBarcode.product_id, ProductBarcode.product_variant_id.in_(variant_ids)).all()}
            for movement in self.db.query(StockHistory).filter(StockHistory.product_variant_id.in_(variant_ids)).order_by(StockHistory.product_variant_id, StockHistory.created_at.desc()).all():
                if movement.product_variant_id not in latest_history:
                    latest_history[movement.product_variant_id] = movement.after_stock
        return [item for product in products for item in self._product_items(product, store_id, barcode_conflicts, latest_history)]

    def summary(self, current_user: User) -> ReconciliationSummary:
        items = self.report(current_user)
        # The first variant item represents one product-level aggregate mismatch.
        product_items = {item.product_id: item for item in items}
        categories = Counter(item.category for item in product_items.values())
        unhealthy = [item for item in product_items.values() if item.category != "HEALTHY"]
        return ReconciliationSummary(total_products=len(product_items), healthy_products=len(product_items) - len(unhealthy), critical_mismatches=sum(1 for item in unhealthy if item.severity == "CRITICAL"), repair_eligible_products=sum(1 for item in unhealthy if item.repair_eligible), categories=dict(categories))

    def repair_preview(self, payload: ReconciliationRepairRequest, current_user: User) -> ReconciliationRepairPreview:
        if payload.confirmation.strip() != REPAIR_CONFIRMATION:
            raise bad_request(f"Type {REPAIR_CONFIRMATION} to preview repairs.", "RECONCILIATION_CONFIRMATION_REQUIRED")
        items = [item for product_id in payload.product_ids for item in self.report(current_user, product_id)]
        blocked = [item for item in items if not item.repair_eligible]
        if blocked:
            raise conflict("Only compatibility aggregate mismatches may be repaired automatically; cost-lot and negative-stock problems require an explicit correction policy.", "RECONCILIATION_REPAIR_NOT_ELIGIBLE")
        return ReconciliationRepairPreview(items=items, total_products=len(set(payload.product_ids)), backup_gate_passed=self._backup_gate(), confirmation_phrase=REPAIR_CONFIRMATION)

    def repair(self, payload: ReconciliationRepairRequest, current_user: User, request_id: str | None) -> ReconciliationRepairResult:
        if payload.confirmation.strip() != REPAIR_CONFIRMATION:
            raise bad_request(f"Type {REPAIR_CONFIRMATION} to repair aggregates.", "RECONCILIATION_CONFIRMATION_REQUIRED")
        # Recreate the owner preview immediately before mutation. This makes the
        # server the safety boundary even when callers skip the UI preview route.
        self.repair_preview(payload, current_user)
        if not self._backup_gate():
            raise conflict("A current successful database backup is required before repairing inventory aggregates.", "RECONCILIATION_BACKUP_REQUIRED")
        store_id = self._store_id(current_user)
        request_hash = hashlib.sha256(json.dumps(sorted(str(value) for value in payload.product_ids)).encode()).hexdigest()
        existing = self.db.query(DestructiveIdempotencyRecord).filter_by(store_id=store_id, user_id=current_user.id, action="INVENTORY_RECONCILIATION_REPAIR", idempotency_key=payload.idempotency_key).first()
        if existing:
            if existing.request_hash != request_hash:
                raise conflict("Idempotency key was previously used with another repair selection.", "RECONCILIATION_IDEMPOTENCY_CONFLICT")
            return ReconciliationRepairResult(repaired_product_ids=[UUID(value) for value in existing.response_snapshot["product_ids"]], already_completed=True)
        try:
            products = self.db.query(Product).filter(Product.store_id == store_id, Product.id.in_(payload.product_ids)).with_for_update().all()
            if len(products) != len(set(payload.product_ids)):
                raise not_found("One or more products")
            repaired: list[UUID] = []
            for product in products:
                variants = list(product.variants)
                expected = sum(variant.current_stock for variant in variants)
                lots = sum(lot.remaining_quantity for variant in variants for lot in variant.cost_lots)
                if any(variant.current_stock < 0 for variant in variants) or lots != expected:
                    raise conflict("Cost-lot or negative-stock discrepancies cannot be repaired automatically.", "RECONCILIATION_REPAIR_NOT_ELIGIBLE")
                inventory = self.db.query(ProductInventory).filter_by(product_id=product.id, store_id=store_id).with_for_update().first()
                before = {"product_current_stock": product.current_stock, "product_inventory_current_stock": inventory.current_stock if inventory else None, "variant_total": expected}
                if product.current_stock == expected and inventory and inventory.current_stock == expected:
                    continue
                product.current_stock = expected
                if not inventory:
                    inventory = ProductInventory(product_id=product.id, store_id=store_id, current_stock=expected, minimum_stock=product.minimum_stock)
                    self.db.add(inventory)
                else:
                    inventory.current_stock = expected
                self.db.add(InventoryReconciliationAudit(store_id=store_id, product_id=product.id, performed_by=current_user.id, idempotency_key=payload.idempotency_key, request_id=request_id, before_values=before, after_values={"product_current_stock": expected, "product_inventory_current_stock": expected, "variant_total": expected}))
                repaired.append(product.id)
            snapshot = {"product_ids": [str(value) for value in repaired]}
            self.db.add(DestructiveIdempotencyRecord(store_id=store_id, user_id=current_user.id, action="INVENTORY_RECONCILIATION_REPAIR", idempotency_key=payload.idempotency_key, request_hash=request_hash, response_snapshot=snapshot))
            self.db.commit()
            return ReconciliationRepairResult(repaired_product_ids=repaired)
        except Exception:
            self.db.rollback()
            raise

    @staticmethod
    def _store_id(current_user: User) -> UUID:
        if not current_user.store_id:
            raise bad_request("Current user is not assigned to a store.", "STORE_REQUIRED")
        return current_user.store_id

    def _product_items(self, product: Product, store_id: UUID, barcode_conflicts: set[UUID] | None = None, latest_history: dict[UUID, int] | None = None) -> list[ReconciliationItem]:
        variants = list(product.variants)
        expected = sum(variant.current_stock for variant in variants)
        inventory = next((item for item in product.inventory_items if item.store_id == store_id), None)
        result: list[ReconciliationItem] = []
        barcode_conflicts = barcode_conflicts or set()
        latest_history = latest_history or {}
        if not variants:
            if product.current_stock == 0:
                return [self._item(product, None, 0, product.current_stock, inventory.current_stock if inventory else None, 0, expected, "LEGACY_CATALOG_ONLY", "WARNING", "Zero-stock catalog-only record has no sellable variants; it does not affect inventory.", False)]
            return [self._item(product, None, 0, product.current_stock, inventory.current_stock if inventory else None, 0, expected, "ORPHAN_VARIANT", "CRITICAL", "Product has no sellable variant records.", False)]
        for variant in variants:
            lots = sum(lot.remaining_quantity for lot in variant.cost_lots)
            category, severity, cause, repair = "HEALTHY", "INFO", "Variant and compatibility aggregates reconcile.", False
            if variant.current_stock < 0:
                category, severity, cause = "NEGATIVE_STOCK", "CRITICAL", "Authoritative variant stock is negative."
            elif variant.id in barcode_conflicts:
                category, severity, cause = "BARCODE_MAPPING_CONFLICT", "CRITICAL", "Barcode mapping refers to a different product than its variant."
            elif variant.id in latest_history and latest_history[variant.id] != variant.current_stock:
                category, severity, cause = "STOCK_HISTORY_MISMATCH", "WARNING", "Latest recorded variant movement does not match authoritative variant stock."
            elif lots < variant.current_stock:
                category, severity, cause = "COST_LOT_SHORTAGE", "CRITICAL", "Available cost lots do not cover authoritative variant stock."
            elif lots > variant.current_stock:
                category, severity, cause = "COST_LOT_EXCESS", "WARNING", "Cost lots exceed authoritative variant stock."
            elif product.current_stock != expected:
                category, severity, cause, repair = "PRODUCT_AGGREGATE_MISMATCH", "WARNING", "Product compatibility aggregate differs from the variant total.", True
            elif not inventory or inventory.current_stock != expected:
                if expected == 0 and product.current_stock == 0 and not inventory:
                    category, severity, cause, repair = "LEGACY_STORE_INVENTORY_ABSENT", "WARNING", "Zero-stock legacy record has no store compatibility aggregate; it does not affect inventory.", False
                else:
                    category, severity, cause, repair = "STORE_INVENTORY_MISMATCH", "WARNING", "Store compatibility aggregate differs from the variant total.", True
            result.append(self._item(product, variant.id, variant.current_stock, product.current_stock, inventory.current_stock if inventory else None, lots, expected, category, severity, cause, repair))
        return result

    @staticmethod
    def _item(product: Product, variant_id: UUID | None, variant_stock: int, product_stock: int, inventory_stock: int | None, lots: int, expected: int, category: str, severity: str, cause: str, repair: bool) -> ReconciliationItem:
        actual = variant_stock if category.startswith("COST_LOT") else product_stock if category == "PRODUCT_AGGREGATE_MISMATCH" else inventory_stock if category == "STORE_INVENTORY_MISMATCH" else expected
        return ReconciliationItem(product_id=product.id, variant_id=variant_id, product_name=product.name, variant_stock=variant_stock, product_stock=product_stock, product_inventory_stock=inventory_stock, remaining_cost_lot_quantity=lots, expected_product_stock=expected, difference=(actual or 0) - expected, severity=severity, category=category, likely_cause=cause, repair_eligible=repair)

    def _backup_gate(self) -> bool:
        if self.settings.allow_test_opening_stock_import_bypass and self.settings.app_env.lower() in {"test", "testing"}:
            return True
        state = BackupStatusService(self.settings.backup_status_dir).status()
        database = next((item for item in state.components if item.component == "database"), None)
        return bool(state.configured and database and database.available and database.status.lower() == "success")
