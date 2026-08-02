from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.exceptions import bad_request, conflict, error_payload, not_found
from app.models.destructive_action import DestructiveIdempotencyRecord
from app.models.enums import StockMovementType
from app.models.product import Product
from app.models.product_inventory import ProductInventory
from app.models.product_variant import ProductVariant
from app.models.product_variant import InventoryCostLot
from app.models.stock_audit_event import StockAuditEvent
from app.models.stock_history import StockHistory
from app.models.user import User
from app.repositories.stock import StockHistoryRepository
from app.schemas.stock import StockAdjustmentCreate, StockCorrectionCreate, StockResetConfirmRequest, StockResetPreviewRequest
from app.services.deletion_security_service import DeletePasswordConfigurationError, DeletePasswordInvalidError, verify_delete_password


class StockService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = StockHistoryRepository(db)

    def history(
        self,
        skip: int = 0,
        limit: int = 100,
        product_id: Optional[UUID] = None,
        movement_type: Optional[StockMovementType] = None,
        store_id: Optional[UUID] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> list[StockHistory]:
        return self.repo.list_recent(skip, limit, product_id, movement_type, store_id, from_date, to_date)

    def adjust(self, payload: StockAdjustmentCreate, current_user: User) -> StockHistory:
        if not current_user.store_id:
            raise bad_request("Current user is not assigned to a store")
        if payload.product_variant_id:
            return self._adjust_variant(payload, current_user)

        product = self.db.query(Product).filter(Product.id == payload.product_id, Product.store_id == current_user.store_id).first()
        if not product:
            raise not_found("Product")

        if payload.reason == "CUSTOMER_RETURN" and payload.direction != "INCREASE":
            raise bad_request("Customer returns must increase stock")
        if payload.reason in {"SUPPLIER_RETURN", "DAMAGE"} and payload.direction != "DECREASE":
            raise bad_request(f"{payload.reason.replace('_', ' ').title()} must decrease stock")

        before_stock = product.current_stock
        if payload.direction == "INCREASE":
            after_stock = before_stock + payload.qty
        else:
            after_stock = before_stock - payload.qty
            if after_stock < 0:
                raise bad_request("Stock cannot become negative")

        product.current_stock = after_stock
        inventory = self._get_or_create_inventory(product.id, current_user.store_id)
        inventory.current_stock = after_stock

        movement = StockHistory(
            product_id=product.id,
            store_id=current_user.store_id,
            movement_type=StockMovementType(payload.reason),
            qty=payload.qty,
            before_stock=before_stock,
            after_stock=after_stock,
            reference=payload.reference,
            created_by=current_user.id,
            request_id=None,
        )
        self.db.add(movement)
        self.db.commit()
        self.db.refresh(movement)
        return movement

    def reset_preview(self, payload: StockResetPreviewRequest, current_user: User, request_id: str) -> dict:
        store_id = self._store_id(current_user)
        variants = self._reset_variants(payload, store_id, positive_only=True, lock=False)
        response = self._reset_response(variants, request_id, [])
        self._audit(
            "STOCK_RESET_PREVIEWED",
            current_user,
            request_id,
            metadata={"scope": payload.scope, "variant_count": response["total_variants"], "total_pieces": response["total_pieces"]},
        )
        self.db.commit()
        return response

    def reset_existing_stock(
        self,
        payload: StockResetConfirmRequest,
        current_user: User,
        idempotency_key: str,
        request_id: str,
    ) -> dict:
        store_id = self._store_id(current_user)
        cached = self._idempotent_reset(payload, current_user, idempotency_key, request_id)
        if cached:
            cached["already_completed"] = True
            return cached
        self._verify_owner_reset_password(payload.owner_password, request_id)

        try:
            variants = self._reset_variants(payload, store_id, positive_only=True, lock=True)
            if not variants:
                response = self._reset_response([], request_id, [], already_completed=False)
                self._store_idempotent_reset(payload, current_user, idempotency_key, response)
                self._audit("STOCK_RESET_COMPLETED", current_user, request_id, metadata={"variant_count": 0, "total_pieces": 0})
                self.db.commit()
                return response

            stock_history_ids: list[UUID] = []
            affected_product_ids: set[UUID] = set()
            response = self._reset_response(variants, request_id, [], already_completed=False)
            for variant in variants:
                before_stock = variant.current_stock
                if before_stock <= 0:
                    continue
                affected_product_ids.add(variant.product_id)
                unit_cost = self._variant_unit_cost(variant)
                variant.current_stock = 0
                self._zero_variant_cost_lots(variant.id)
                movement = StockHistory(
                    product_id=variant.product_id,
                    product_variant_id=variant.id,
                    store_id=store_id,
                    movement_type=StockMovementType.STOCK_RESET_OUT,
                    qty=before_stock,
                    before_stock=before_stock,
                    after_stock=0,
                    reference=f"STOCK-RESET-{request_id}",
                    created_by=current_user.id,
                    request_id=request_id,
                    unit_cost=unit_cost,
                )
                self.db.add(movement)
                self.db.flush()
                stock_history_ids.append(movement.id)
                self._audit(
                    "STOCK_RESET_COMPLETED",
                    current_user,
                    request_id,
                    product_id=variant.product_id,
                    product_variant_id=variant.id,
                    previous_quantity=before_stock,
                    adjustment_quantity=-before_stock,
                    resulting_quantity=0,
                    metadata={"barcode": variant.barcode, "sku": variant.internal_sku},
                )

            for product_id in affected_product_ids:
                self._sync_product_stock(product_id, store_id)
            response["stock_history_ids"] = [str(item) for item in stock_history_ids]
            self._store_idempotent_reset(payload, current_user, idempotency_key, response)
            self.db.commit()
            return response
        except Exception:
            self.db.rollback()
            self._audit("STOCK_RESET_FAILED", current_user, request_id, metadata={"scope": payload.scope})
            self.db.commit()
            raise

    def correct_transaction(self, transaction_id: UUID, payload: StockCorrectionCreate, current_user: User) -> StockHistory:
        """Append a correction; the original movement is immutable evidence."""
        store_id = current_user.store_id
        if not store_id:
            raise bad_request("Current user is not assigned to a store")
        original = (
            self.db.query(StockHistory)
            .filter(StockHistory.id == transaction_id, StockHistory.store_id == store_id)
            .with_for_update()
            .first()
        )
        if not original:
            raise not_found("Stock transaction")
        if original.correction_of_id:
            raise conflict("A correction transaction cannot be corrected again. Correct the original transaction instead.")
        delta = payload.correct_quantity - original.after_stock
        if delta == 0:
            raise bad_request("The corrected quantity matches the original record; no correction is needed")
        product = self.db.query(Product).filter(Product.id == original.product_id, Product.store_id == store_id).with_for_update().first()
        if not product:
            raise not_found("Product")
        if original.product_variant_id:
            variant = self.db.query(ProductVariant).filter(ProductVariant.id == original.product_variant_id, ProductVariant.store_id == store_id).with_for_update().first()
            if not variant:
                raise not_found("Product variant")
            before_stock = variant.current_stock
            after_stock = before_stock + delta
            if after_stock < 0:
                raise bad_request("This correction would make variant stock negative")
            variant.current_stock = after_stock
            self.db.flush()
            self._sync_product_stock(product.id, store_id)
        else:
            before_stock, after_stock = product.current_stock, product.current_stock + delta
            if after_stock < 0:
                raise bad_request("This correction would make current stock negative")
            product.current_stock = after_stock
            inventory = self._get_or_create_inventory(product.id, store_id)
            inventory.current_stock = after_stock
        movement = StockHistory(
            product_id=product.id,
            product_variant_id=original.product_variant_id,
            store_id=store_id,
            movement_type=StockMovementType.MANUAL_ADJUSTMENT,
            qty=abs(delta),
            before_stock=before_stock,
            after_stock=after_stock,
            reference=payload.reference or f"CORRECTION-{original.id}",
            created_by=current_user.id,
            correction_of_id=original.id,
            correction_reason=payload.reason,
            correction_notes=(payload.notes or "").strip() or None,
            request_id=None,
        )
        self.db.add(movement)
        self.db.commit()
        self.db.refresh(movement)
        return movement

    def _adjust_variant(self, payload: StockAdjustmentCreate, current_user: User) -> StockHistory:
        store_id = self._store_id(current_user)
        variant = (
            self.db.query(ProductVariant)
            .options(joinedload(ProductVariant.product))
            .filter(ProductVariant.id == payload.product_variant_id, ProductVariant.store_id == store_id)
            .with_for_update()
            .first()
        )
        if not variant or not variant.product:
            raise not_found("Product variant")
        if payload.product_id and payload.product_id != variant.product_id:
            raise bad_request("Product does not match the selected variant")
        if payload.reason == "CUSTOMER_RETURN" and payload.direction != "INCREASE":
            raise bad_request("Customer returns must increase stock")
        if payload.reason in {"SUPPLIER_RETURN", "DAMAGE"} and payload.direction != "DECREASE":
            raise bad_request(f"{payload.reason.replace('_', ' ').title()} must decrease stock")

        before_stock = variant.current_stock
        if payload.adjustment_type == "SET_COUNTED_QUANTITY":
            after_stock = payload.qty
            delta = after_stock - before_stock
        else:
            delta = payload.qty if payload.direction == "INCREASE" else -payload.qty
            after_stock = before_stock + delta
        if delta == 0:
            raise bad_request("The counted quantity matches current stock; no movement is needed")
        if after_stock < 0:
            raise bad_request("Stock cannot become negative")

        variant.current_stock = after_stock
        if delta < 0:
            self._consume_variant_cost_lots(variant.id, abs(delta))
        elif delta > 0:
            self._create_adjustment_cost_lot(variant, delta, payload.reference)
        self.db.flush()
        self._sync_product_stock(variant.product_id, store_id)
        movement_type = (
            StockMovementType.STOCK_COUNT_IN
            if payload.adjustment_type == "SET_COUNTED_QUANTITY" and delta > 0
            else StockMovementType.STOCK_COUNT_OUT
            if payload.adjustment_type == "SET_COUNTED_QUANTITY" and delta < 0
            else StockMovementType(payload.reason)
        )
        movement = StockHistory(
            product_id=variant.product_id,
            product_variant_id=variant.id,
            store_id=store_id,
            movement_type=movement_type,
            qty=abs(delta),
            before_stock=before_stock,
            after_stock=after_stock,
            reference=payload.reference,
            created_by=current_user.id,
            unit_cost=self._variant_unit_cost(variant),
        )
        self.db.add(movement)
        self._audit(
            "VARIANT_STOCK_ADJUSTED",
            current_user,
            payload.reference,
            product_id=variant.product_id,
            product_variant_id=variant.id,
            previous_quantity=before_stock,
            adjustment_quantity=delta,
            resulting_quantity=after_stock,
            metadata={"reason": payload.reason, "adjustment_type": payload.adjustment_type},
        )
        self.db.commit()
        self.db.refresh(movement)
        return movement

    def _get_or_create_inventory(self, product_id: UUID, store_id: Optional[UUID]) -> ProductInventory:
        if store_id is None:
            raise bad_request("Current user is not assigned to a store")
        inventory = (
            self.db.query(ProductInventory)
            .filter(ProductInventory.product_id == product_id, ProductInventory.store_id == store_id)
            .first()
        )
        if inventory:
            return inventory
        inventory = ProductInventory(product_id=product_id, store_id=store_id, current_stock=0, minimum_stock=0)
        self.db.add(inventory)
        self.db.flush()
        return inventory

    def _reset_variants(self, payload: StockResetPreviewRequest, store_id: UUID, positive_only: bool, lock: bool) -> list[ProductVariant]:
        query = (
            self.db.query(ProductVariant)
            .join(Product, Product.id == ProductVariant.product_id)
            .options(joinedload(ProductVariant.product).joinedload(Product.brand), joinedload(ProductVariant.product).joinedload(Product.category))
            .filter(ProductVariant.store_id == store_id, Product.store_id == store_id)
        )
        if positive_only:
            query = query.filter(ProductVariant.current_stock > 0)
        if payload.scope == "SELECTED_VARIANTS":
            query = query.filter(ProductVariant.id.in_(payload.variant_ids))
        elif payload.scope == "PRODUCT":
            query = query.filter(ProductVariant.product_id == payload.product_id)
        elif payload.scope == "CATEGORY":
            query = query.filter(Product.category_id == payload.category_id)
        elif payload.scope == "BRAND":
            query = query.filter(Product.brand_id == payload.brand_id)
        elif payload.scope == "ALL_OPENING_STOCK":
            opening_variant_ids = [
                row[0]
                for row in self.db.query(StockHistory.product_variant_id)
                .filter(
                    StockHistory.store_id == store_id,
                    StockHistory.product_variant_id.isnot(None),
                    StockHistory.movement_type == StockMovementType.OPENING_STOCK,
                )
                .distinct()
                .all()
            ]
            if not opening_variant_ids:
                return []
            query = query.filter(ProductVariant.id.in_(opening_variant_ids))
        elif payload.scope != "ALL_CURRENT_STOCK":
            raise bad_request("Unsupported reset scope")
        if lock:
            query = query.with_for_update(of=ProductVariant)
        variants = query.order_by(Product.name, ProductVariant.size, ProductVariant.color).all()
        if payload.scope == "SELECTED_VARIANTS":
            found_ids = {variant.id for variant in variants}
            missing_ids = set(payload.variant_ids) - found_ids
            if missing_ids and not positive_only:
                raise not_found("One or more selected variants")
        return variants

    def _reset_response(
        self,
        variants: list[ProductVariant],
        request_id: str,
        stock_history_ids: list[UUID],
        already_completed: bool = False,
    ) -> dict:
        items = []
        total_value = Decimal("0")
        for variant in variants:
            stock = max(variant.current_stock, 0)
            unit_cost = self._variant_unit_cost(variant)
            value = unit_cost * stock
            total_value += value
            product = variant.product
            items.append(
                {
                    "variant_id": str(variant.id),
                    "product_id": str(variant.product_id),
                    "product": product.name if product else "Product",
                    "brand": product.brand.name if product and product.brand else None,
                    "category": product.category.name if product and product.category else None,
                    "size": variant.size,
                    "color": variant.color,
                    "barcode": variant.barcode,
                    "sku": variant.internal_sku,
                    "current_stock": stock,
                    "reset_quantity": -stock,
                    "resulting_stock": 0,
                    "unit_cost": str(unit_cost),
                    "inventory_value": str(value),
                }
            )
        return {
            "variants": items,
            "total_products": len({item["product_id"] for item in items}),
            "total_variants": len(items),
            "total_pieces": sum(item["current_stock"] for item in items),
            "total_inventory_value": str(total_value),
            "request_id": request_id,
            "stock_history_ids": [str(item) for item in stock_history_ids],
            "already_completed": already_completed,
            "classification_warning": None,
        }

    def _sync_product_stock(self, product_id: UUID, store_id: UUID) -> None:
        total = self.db.query(func.coalesce(func.sum(ProductVariant.current_stock), 0)).filter(ProductVariant.product_id == product_id, ProductVariant.store_id == store_id).scalar() or 0
        product = self.db.query(Product).filter(Product.id == product_id, Product.store_id == store_id).with_for_update().first()
        if not product:
            raise not_found("Product")
        product.current_stock = int(total)
        inventory = self._get_or_create_inventory(product_id, store_id)
        inventory.current_stock = int(total)

    def _consume_variant_cost_lots(self, variant_id: UUID, quantity: int) -> None:
        remaining = quantity
        lots = (
            self.db.query(InventoryCostLot)
            .filter(InventoryCostLot.product_variant_id == variant_id, InventoryCostLot.remaining_quantity > 0)
            .order_by(InventoryCostLot.received_date, InventoryCostLot.created_at, InventoryCostLot.id)
            .with_for_update()
            .all()
        )
        for lot in lots:
            if remaining <= 0:
                break
            consumed = min(remaining, lot.remaining_quantity)
            lot.remaining_quantity -= consumed
            remaining -= consumed

    def _zero_variant_cost_lots(self, variant_id: UUID) -> None:
        for lot in (
            self.db.query(InventoryCostLot)
            .filter(InventoryCostLot.product_variant_id == variant_id, InventoryCostLot.remaining_quantity > 0)
            .with_for_update()
            .all()
        ):
            lot.remaining_quantity = 0

    def _create_adjustment_cost_lot(self, variant: ProductVariant, quantity: int, reference: str) -> None:
        unit_cost = self._variant_unit_cost(variant)
        self.db.add(
            InventoryCostLot(
                store_id=variant.store_id,
                product_variant_id=variant.id,
                received_quantity=quantity,
                remaining_quantity=quantity,
                unit_purchase_cost=unit_cost,
                allocated_landed_cost=Decimal("0"),
                effective_unit_cost=unit_cost,
                lot_reference=reference,
            )
        )

    @staticmethod
    def _variant_unit_cost(variant: ProductVariant) -> Decimal:
        return Decimal(variant.average_cost or variant.last_purchase_cost or getattr(variant.product, "purchase_price", 0) or 0)

    def _audit(
        self,
        event_type: str,
        current_user: User,
        request_id: str,
        product_id: UUID | None = None,
        product_variant_id: UUID | None = None,
        previous_quantity: int | None = None,
        adjustment_quantity: int | None = None,
        resulting_quantity: int | None = None,
        metadata: dict | None = None,
    ) -> None:
        self.db.add(
            StockAuditEvent(
                event_type=event_type,
                store_id=self._store_id(current_user),
                user_id=current_user.id,
                user_role=current_user.role.value,
                product_id=product_id,
                product_variant_id=product_variant_id,
                previous_quantity=previous_quantity,
                adjustment_quantity=adjustment_quantity,
                resulting_quantity=resulting_quantity,
                request_id=request_id,
                metadata_json=metadata or {},
            )
        )

    def _verify_owner_reset_password(self, owner_password: str | None, request_id: str) -> None:
        if not get_settings().delete_auth_password_hash:
            return
        try:
            verify_delete_password(owner_password or "")
        except DeletePasswordConfigurationError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={**error_payload("Deletion-password protection is not configured.", "DELETE_PASSWORD_NOT_CONFIGURED"), "request_id": request_id}) from exc
        except DeletePasswordInvalidError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={**error_payload("The owner password is incorrect.", "DELETE_PASSWORD_INVALID"), "request_id": request_id}) from exc

    def _idempotent_reset(self, payload: StockResetConfirmRequest, user: User, key: str, request_id: str) -> dict | None:
        if not key:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={**error_payload("Idempotency-Key header is required", "IDEMPOTENCY_KEY_REQUIRED"), "request_id": request_id})
        record = self.db.query(DestructiveIdempotencyRecord).filter_by(store_id=self._store_id(user), user_id=user.id, action="STOCK_RESET", idempotency_key=key).first()
        digest = self._reset_request_hash(payload)
        if record and record.request_hash != digest:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={**error_payload("This idempotency key was already used for a different reset request.", "IDEMPOTENCY_KEY_REUSED"), "request_id": request_id})
        return record.response_snapshot if record else None

    def _store_idempotent_reset(self, payload: StockResetConfirmRequest, user: User, key: str, response: dict) -> None:
        self.db.add(DestructiveIdempotencyRecord(store_id=self._store_id(user), user_id=user.id, action="STOCK_RESET", idempotency_key=key, request_hash=self._reset_request_hash(payload), response_snapshot=response))

    @staticmethod
    def _reset_request_hash(payload: StockResetPreviewRequest) -> str:
        parts = [
            payload.scope,
            str(payload.product_id or ""),
            str(payload.category_id or ""),
            str(payload.brand_id or ""),
            ",".join(sorted(str(item) for item in payload.variant_ids)),
        ]
        return hashlib.sha256(":".join(parts).encode()).hexdigest()

    @staticmethod
    def _store_id(current_user: User) -> UUID:
        if not current_user.store_id:
            raise bad_request("Current user is not assigned to a store")
        return current_user.store_id
