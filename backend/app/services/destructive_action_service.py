from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.exceptions import error_payload, not_found
from app.core.security import verify_password
from app.models.destructive_action import DeletePasswordAttempt, DestructiveActionAudit, DestructiveIdempotencyRecord, StoreSecuritySetting
from app.models.enums import PurchaseStatus, SaleStatus, StockMovementType
from app.models.product import Product
from app.models.product_inventory import ProductInventory
from app.models.product_variant import ProductVariant
from app.models.purchase import Purchase
from app.models.purchase_audit import PurchaseAudit
from app.models.purchase_item import PurchaseItem
from app.models.sale import Sale, SaleAudit, SaleItem, SaleReturn
from app.models.stock_history import StockHistory
from app.models.user import User
from app.services.deletion_security_service import DeletePasswordConfigurationError, DeletePasswordInvalidError, hash_delete_password, verify_delete_password, verify_delete_password_hash


class DestructiveActionService:
    """Owner-only, password-confirmed deletion flows with a durable audit trail."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def security(self, user: User) -> dict:
        setting = self.db.get(StoreSecuritySetting, self._store_id(user))
        return {
            "require_password_for_sale_delete": setting.require_password_for_sale_delete if setting else True,
            "require_password_for_purchase_delete": setting.require_password_for_purchase_delete if setting else True,
            "configured": bool(setting and setting.delete_password_hash) or bool(get_settings().delete_auth_password_hash),
        }

    def configure_delete_password(self, current_credential: str, new_password: str, user: User, request_id: str, client_ip: str | None) -> dict:
        """Set or rotate a per-store deletion password after re-authenticating the Owner."""
        if not verify_password(current_credential, user.password_hash):
            self._audit("DELETE_PASSWORD_CONFIGURATION_FAILED", user, request_id, client_ip)
            self.db.commit()
            self._error(status.HTTP_403_FORBIDDEN, "The current Owner password is incorrect.", "OWNER_CREDENTIAL_INVALID", request_id)

        store_id = self._store_id(user)
        setting = self.db.get(StoreSecuritySetting, store_id)
        changed = bool(setting and setting.delete_password_hash)
        if not setting:
            setting = StoreSecuritySetting(
                store_id=store_id,
                require_password_for_sale_delete=True,
                require_password_for_purchase_delete=True,
                updated_by=user.id,
            )
            self.db.add(setting)
        setting.delete_password_hash = hash_delete_password(new_password)
        setting.updated_by = user.id
        self._audit(
            "DELETE_PASSWORD_CHANGED" if changed else "DELETE_PASSWORD_CONFIGURED",
            user,
            request_id,
            client_ip,
            record_counts={"password_changed": 1},
        )
        self.db.commit()
        return self.security(user)

    def check_purchases(self, ids: list[UUID], user: User, request_id: str) -> dict:
        purchases = self._purchases(ids, user, lock=False)
        deletable, requires_void, blocked = [], [], []
        for purchase in purchases:
            movements = self.db.query(StockHistory).filter(StockHistory.purchase_id == purchase.id).all()
            if purchase.status == PurchaseStatus.VOIDED:
                blocked.append(self._entry(purchase.id, purchase.invoice_number, "This transaction has already been voided.", request_id))
            elif purchase.status in {PurchaseStatus.DRAFT, PurchaseStatus.CANCELLED} or purchase.ai_processing_status == "FAILED":
                if movements:
                    requires_void.append(self._entry(purchase.id, purchase.invoice_number, None, request_id, len(movements)))
                else:
                    deletable.append(self._entry(purchase.id, purchase.invoice_number, None, request_id))
            elif purchase.status == PurchaseStatus.CONFIRMED:
                issue = self._purchase_reversal_issue(movements, self._store_id(user)) or self._variant_reversal_issue([movement.product_id for movement in movements])
                if issue:
                    blocked.append(self._entry(purchase.id, purchase.invoice_number, issue, request_id, len(movements)))
                else:
                    requires_void.append(self._entry(purchase.id, purchase.invoice_number, None, request_id, len(movements)))
            else:
                blocked.append(self._entry(purchase.id, purchase.invoice_number, "This purchase cannot be deleted safely.", request_id))
        return {"deletable": deletable, "requires_void": requires_void, "blocked": blocked, "request_id": request_id}

    def check_sales(self, ids: list[UUID], user: User, request_id: str) -> dict:
        sales = self._sales(ids, user, lock=False)
        deletable, requires_void, blocked = [], [], []
        for sale in sales:
            movements = self.db.query(StockHistory).filter(StockHistory.sale_id == sale.id).count()
            returns = self.db.query(SaleReturn).filter(SaleReturn.sale_id == sale.id).count()
            if sale.status == SaleStatus.VOIDED:
                blocked.append(self._entry(sale.id, sale.invoice_number, "This transaction has already been voided.", request_id))
            elif returns:
                blocked.append(self._entry(sale.id, sale.invoice_number, "This sale cannot be deleted because it has a completed return or exchange.", request_id, movements))
            elif sale.status in {SaleStatus.DRAFT, SaleStatus.CANCELLED} and not movements:
                deletable.append(self._entry(sale.id, sale.invoice_number, None, request_id))
            elif sale.status in {SaleStatus.COMPLETED, SaleStatus.EDITED, SaleStatus.PARTIALLY_RETURNED, SaleStatus.RETURNED}:
                issue = self._variant_reversal_issue([item.product_id for item in sale.items])
                if issue:
                    blocked.append(self._entry(sale.id, sale.invoice_number, issue, request_id, movements))
                else:
                    requires_void.append(self._entry(sale.id, sale.invoice_number, None, request_id, movements))
            else:
                blocked.append(self._entry(sale.id, sale.invoice_number, "This sale cannot be deleted safely.", request_id, movements))
        return {"deletable": deletable, "requires_void": requires_void, "blocked": blocked, "request_id": request_id}

    def delete_purchases(self, ids: list[UUID], password: str, key: str, user: User, request_id: str, client_ip: str | None) -> dict:
        cached = self._idempotent("PURCHASE_DELETE", ids, key, user, request_id)
        if cached:
            return cached
        self._verify_password(password, user, request_id, client_ip)
        purchases = self._purchases(ids, user, lock=True)
        result = {"deleted": [], "voided": [], "request_id": request_id}
        try:
            for purchase in purchases:
                movements = self.db.query(StockHistory).filter(StockHistory.purchase_id == purchase.id).with_for_update().all()
                if purchase.status == PurchaseStatus.VOIDED:
                    self._error(status.HTTP_409_CONFLICT, "This transaction has already been voided.", "PURCHASE_ALREADY_VOIDED", request_id)
                if purchase.status == PurchaseStatus.CONFIRMED or movements:
                    issue = self._purchase_reversal_issue(movements, self._store_id(user)) or self._variant_reversal_issue([movement.product_id for movement in movements])
                    if issue:
                        self._error(status.HTTP_409_CONFLICT, issue, "PURCHASE_STOCK_USED", request_id)
                    original_status = purchase.status.value
                    reversal_ids = self._reverse_purchase(purchase, movements, user, request_id)
                    result["voided"].append({"id": str(purchase.id), "mode": "VOID_AND_REVERSE"})
                    self._audit("PURCHASE_VOIDED", user, request_id, client_ip, "PURCHASE", purchase.id, purchase.invoice_number, original_status, "VOID_AND_REVERSE", {"stock_movements": len(movements)}, reversal_ids)
                else:
                    reference, original = purchase.invoice_number, purchase.status.value
                    item_count = len(purchase.items)
                    self.db.delete(purchase)
                    result["deleted"].append({"id": str(purchase.id), "mode": "PERMANENT_DELETE"})
                    self._audit("PURCHASE_PERMANENTLY_DELETED", user, request_id, client_ip, "PURCHASE", purchase.id, reference, original, "PERMANENT_DELETE", {"purchase_items": item_count}, [])
            self._audit("BULK_PURCHASE_DELETE_COMPLETED", user, request_id, client_ip, record_counts={"deleted": len(result["deleted"]), "voided": len(result["voided"])})
            self._store_idempotent("PURCHASE_DELETE", ids, key, user, result)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return result

    def delete_sales(self, ids: list[UUID], password: str, key: str, user: User, request_id: str, client_ip: str | None) -> dict:
        cached = self._idempotent("SALE_DELETE", ids, key, user, request_id)
        if cached:
            return cached
        self._verify_password(password, user, request_id, client_ip)
        sales = self._sales(ids, user, lock=True)
        result = {"deleted": [], "voided": [], "request_id": request_id}
        try:
            for sale in sales:
                if sale.status == SaleStatus.VOIDED:
                    self._error(status.HTTP_409_CONFLICT, "This transaction has already been voided.", "SALE_ALREADY_VOIDED", request_id)
                if sale.returns:
                    self._error(status.HTTP_409_CONFLICT, "This sale cannot be deleted because it has a completed return or exchange.", "SALE_HAS_RETURN", request_id)
                movements = self.db.query(StockHistory).filter(StockHistory.sale_id == sale.id).count()
                if sale.status in {SaleStatus.DRAFT, SaleStatus.CANCELLED} and not movements:
                    reference, original, item_count = sale.invoice_number, sale.status.value, len(sale.items)
                    self.db.delete(sale)
                    result["deleted"].append({"id": str(sale.id), "mode": "PERMANENT_DELETE"})
                    self._audit("SALE_PERMANENTLY_DELETED", user, request_id, client_ip, "SALE", sale.id, reference, original, "PERMANENT_DELETE", {"sale_items": item_count}, [])
                else:
                    issue = self._variant_reversal_issue([item.product_id for item in sale.items])
                    if issue:
                        self._error(status.HTTP_409_CONFLICT, issue, "VARIANT_LEDGER_REQUIRED", request_id)
                    original_status = sale.status.value
                    reversal_ids = self._void_sale(sale, user, request_id)
                    result["voided"].append({"id": str(sale.id), "mode": "VOID_AND_REVERSE"})
                    self._audit("SALE_VOIDED", user, request_id, client_ip, "SALE", sale.id, sale.invoice_number, original_status, "VOID_AND_REVERSE", {"sale_items": len(sale.items)}, reversal_ids)
            self._audit("BULK_SALE_DELETE_COMPLETED", user, request_id, client_ip, record_counts={"deleted": len(result["deleted"]), "voided": len(result["voided"])})
            self._store_idempotent("SALE_DELETE", ids, key, user, result)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return result

    def _verify_password(self, password: str, user: User, request_id: str, client_ip: str | None) -> None:
        store_id = self._store_id(user)
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
        failures = self.db.query(func.count(DeletePasswordAttempt.id)).filter(DeletePasswordAttempt.store_id == store_id, DeletePasswordAttempt.user_id == user.id, DeletePasswordAttempt.attempted_at >= cutoff).scalar() or 0
        if failures >= 5:
            self._audit("DELETE_PASSWORD_LOCKED", user, request_id, client_ip)
            self.db.commit()
            self._error(status.HTTP_429_TOO_MANY_REQUESTS, "Too many incorrect attempts. Try again later.", "DELETE_PASSWORD_LOCKED", request_id)
        try:
            setting = self.db.get(StoreSecuritySetting, store_id)
            if setting and setting.delete_password_hash:
                verify_delete_password_hash(password, setting.delete_password_hash)
            else:
                verify_delete_password(password)
        except DeletePasswordConfigurationError:
            self._audit("DELETE_PASSWORD_CONFIGURATION_ERROR", user, request_id, client_ip)
            self.db.commit()
            self._error(status.HTTP_503_SERVICE_UNAVAILABLE, "Deletion-password protection is not configured.", "DELETE_PASSWORD_NOT_CONFIGURED", request_id)
        except DeletePasswordInvalidError:
            self.db.add(DeletePasswordAttempt(store_id=store_id, user_id=user.id))
            self._audit("DELETE_PASSWORD_FAILED", user, request_id, client_ip)
            self.db.commit()
            if failures + 1 >= 5:
                self._error(status.HTTP_429_TOO_MANY_REQUESTS, "Too many incorrect attempts. Try again later.", "DELETE_PASSWORD_LOCKED", request_id)
            self._error(status.HTTP_403_FORBIDDEN, "The deletion password is incorrect.", "DELETE_PASSWORD_INVALID", request_id)
        self.db.query(DeletePasswordAttempt).filter(DeletePasswordAttempt.store_id == store_id, DeletePasswordAttempt.user_id == user.id).delete(synchronize_session=False)

    def _reverse_purchase(self, purchase: Purchase, movements: list[StockHistory], user: User, request_id: str) -> list[str]:
        store_id, reversal_ids = self._store_id(user), []
        for movement in movements:
            product = self.db.query(Product).filter(Product.id == movement.product_id).with_for_update().one()
            inventory = self.db.query(ProductInventory).filter(ProductInventory.product_id == product.id, ProductInventory.store_id == store_id).with_for_update().one_or_none()
            if not inventory or inventory.current_stock < movement.qty or product.current_stock < movement.qty:
                self._error(status.HTTP_409_CONFLICT, "This purchase cannot be deleted because some received stock has already been sold, returned or transferred.", "PURCHASE_STOCK_USED", request_id)
            before = product.current_stock
            product.current_stock -= movement.qty
            inventory.current_stock -= movement.qty
            reverse = StockHistory(product_id=product.id, store_id=store_id, movement_type=StockMovementType.PURCHASE_VOID, qty=-movement.qty, before_stock=before, after_stock=product.current_stock, reference=f"{purchase.invoice_number or purchase.id} void", purchase_id=purchase.id, purchase_item_id=movement.purchase_item_id, created_by=user.id)
            self.db.add(reverse)
            self.db.flush()
            reversal_ids.append(str(reverse.id))
        purchase.status, purchase.version, purchase.ai_processing_status = PurchaseStatus.VOIDED, purchase.version + 1, "VOIDED"
        self.db.add(PurchaseAudit(purchase_id=purchase.id, action="VOIDED", reason=None, before_data={"status": "CONFIRMED"}, after_data={"status": "VOIDED"}, performed_by=user.id))
        return reversal_ids

    def _void_sale(self, sale: Sale, user: User, request_id: str) -> list[str]:
        store_id, reversal_ids = self._store_id(user), []
        for item in sale.items:
            product = self.db.query(Product).filter(Product.id == item.product_id).with_for_update().one()
            inventory = self.db.query(ProductInventory).filter(ProductInventory.product_id == product.id, ProductInventory.store_id == store_id).with_for_update().one_or_none()
            if not inventory:
                self._error(status.HTTP_409_CONFLICT, "Inventory record is missing for this sale.", "SALE_INVENTORY_MISSING", request_id)
            before = product.current_stock
            product.current_stock += item.quantity
            inventory.current_stock += item.quantity
            reverse = StockHistory(product_id=product.id, store_id=store_id, movement_type=StockMovementType.SALE_VOID, qty=item.quantity, before_stock=before, after_stock=product.current_stock, reference=f"{sale.invoice_number} void", sale_id=sale.id, sale_item_id=item.id, created_by=user.id)
            self.db.add(reverse)
            self.db.flush()
            reversal_ids.append(str(reverse.id))
        original_status = sale.status.value
        sale.status, sale.version, sale.voided_by, sale.voided_at = SaleStatus.VOIDED, sale.version + 1, user.id, datetime.now(timezone.utc)
        self.db.add(SaleAudit(sale_id=sale.id, action="VOIDED", reason=None, performed_by=user.id, before_data={"status": original_status}, after_data={"status": "VOIDED"}))
        return reversal_ids

    def _purchase_reversal_issue(self, movements: list[StockHistory], store_id: UUID) -> str | None:
        for movement in movements:
            inventory = self.db.query(ProductInventory).filter(ProductInventory.product_id == movement.product_id, ProductInventory.store_id == store_id).first()
            if not inventory or inventory.current_stock < movement.qty:
                return "This purchase cannot be deleted because some received stock has already been sold, returned or transferred."
        return None

    def _variant_reversal_issue(self, product_ids: list[UUID]) -> str | None:
        """Never infer a size or colour when a historical movement lacks a variant ID."""
        for product_id in set(product_ids):
            variant_count = self.db.query(func.count(ProductVariant.id)).filter(ProductVariant.product_id == product_id).scalar() or 0
            if variant_count > 1:
                return "This transaction cannot be voided safely because its historical stock movement has no exact product variant."
        return None

    def _purchases(self, ids: list[UUID], user: User, lock: bool) -> list[Purchase]:
        store_id = self._store_id(user)
        query = self.db.query(Purchase).options(selectinload(Purchase.items)).filter(Purchase.id.in_(list(dict.fromkeys(ids))), Purchase.store_id == store_id)
        if lock: query = query.with_for_update()
        records = query.all()
        if len(records) != len(set(ids)): raise not_found("One or more selected purchases")
        return records

    def _sales(self, ids: list[UUID], user: User, lock: bool) -> list[Sale]:
        store_id = self._store_id(user)
        query = self.db.query(Sale).options(selectinload(Sale.items), selectinload(Sale.returns)).filter(Sale.id.in_(list(dict.fromkeys(ids))), Sale.store_id == store_id)
        if lock: query = query.with_for_update()
        records = query.all()
        if len(records) != len(set(ids)): raise not_found("One or more selected sales")
        return records

    def _idempotent(self, action: str, ids: list[UUID], key: str, user: User, request_id: str) -> dict | None:
        if not key:
            self._error(status.HTTP_422_UNPROCESSABLE_ENTITY, "Idempotency-Key header is required", "IDEMPOTENCY_KEY_REQUIRED", request_id)
        record = self.db.query(DestructiveIdempotencyRecord).filter_by(store_id=self._store_id(user), user_id=user.id, action=action, idempotency_key=key).first()
        digest = self._request_hash(action, ids)
        if record and record.request_hash != digest:
            self._error(status.HTTP_409_CONFLICT, "This idempotency key was already used for a different request.", "IDEMPOTENCY_KEY_REUSED", request_id)
        return record.response_snapshot if record else None

    def _store_idempotent(self, action: str, ids: list[UUID], key: str, user: User, result: dict) -> None:
        self.db.add(DestructiveIdempotencyRecord(store_id=self._store_id(user), user_id=user.id, action=action, idempotency_key=key, request_hash=self._request_hash(action, ids), response_snapshot=result))

    @staticmethod
    def _request_hash(action: str, ids: list[UUID]) -> str:
        return hashlib.sha256(f"{action}:{','.join(sorted(str(item) for item in ids))}".encode()).hexdigest()

    def _audit(self, event: str, user: User, request_id: str, client_ip: str | None, entity_type: str | None = None, entity_id: UUID | None = None, reference: str | None = None, original_status: str | None = None, action: str | None = None, record_counts: dict | None = None, reversal_ids: list[str] | None = None) -> None:
        self.db.add(DestructiveActionAudit(store_id=self._store_id(user), user_id=user.id, user_role=user.role.value, event_type=event, entity_type=entity_type, entity_id=entity_id, reference=reference, original_status=original_status, final_action=action, record_counts=record_counts or {}, reversal_ids=reversal_ids or [], request_id=request_id, client_ip=client_ip))

    @staticmethod
    def _entry(identifier: UUID, reference: str | None, reason: str | None, request_id: str, movements: int = 0) -> dict:
        data = {"id": str(identifier), "reference": reference or "Pending number", "request_id": request_id}
        if reason: data["reason"] = reason
        if movements: data["inventory_transactions"] = movements
        return data

    @staticmethod
    def _store_id(user: User) -> UUID:
        if not user.store_id: raise HTTPException(status_code=400, detail=error_payload("Current user is not assigned to an active store.", "STORE_SCOPE_REQUIRED"))
        return user.store_id

    @staticmethod
    def _error(code: int, message: str, error_code: str, request_id: str) -> None:
        raise HTTPException(status_code=code, detail={**error_payload(message, error_code), "request_id": request_id})
