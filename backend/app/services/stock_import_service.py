from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Protocol
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import bad_request, conflict, not_found
from app.models.enums import StockMovementType
from app.models.product import Product
from app.models.product_inventory import ProductInventory
from app.models.product_variant import ProductVariant
from app.models.stock_history import StockHistory
from app.models.stock_import import StockImport, StockImportBackup, StockImportRollback, StockImportRow
from app.models.user import User


OPENING_STOCK = "OPENING_STOCK"
READY = "READY"
COMPLETED = "COMPLETED"


@dataclass(frozen=True)
class BackupResult:
    path: str
    sha256: str
    size_bytes: int
    metadata: dict


class BackupRunner(Protocol):
    def run(self, stock_import: StockImport) -> BackupResult: ...


class UnconfiguredBackupRunner:
    """Fail closed until the deployment backup command is configured."""

    def run(self, stock_import: StockImport) -> BackupResult:
        raise RuntimeError("The verified pre-import backup command is not configured")


class StockImportService:
    def __init__(self, db: Session, backup_runner: BackupRunner | None = None) -> None:
        self.db = db
        self.backup_runner = backup_runner or UnconfiguredBackupRunner()

    def upload_opening_stock(self, content: bytes, filename: str, idempotency_key: str, current_user: User, request_id: str) -> StockImport:
        if not idempotency_key.strip():
            raise bad_request("Idempotency-Key is required for an opening-stock import", "IDEMPOTENCY_KEY_REQUIRED")
        if not filename.lower().endswith(".csv"):
            raise bad_request("Only CSV opening-stock files are accepted", "OPENING_STOCK_CSV_REQUIRED")
        digest = hashlib.sha256(content).hexdigest()
        existing = self.db.query(StockImport).filter(StockImport.store_id == current_user.store_id, StockImport.idempotency_key == idempotency_key).first()
        if existing:
            if existing.file_sha256 != digest:
                raise conflict("This idempotency key was already used with a different file", "IDEMPOTENCY_KEY_REUSED")
            return existing
        stock_import = StockImport(store_id=current_user.store_id, import_type=OPENING_STOCK, status="UPLOADED", source_filename=Path(filename).name, file_sha256=digest, idempotency_key=idempotency_key, uploaded_by=current_user.id, request_id=request_id, summary={})
        self.db.add(stock_import)
        self.db.flush()
        self._validate_upload(stock_import, content)
        self.db.commit()
        return stock_import

    def get(self, import_id: UUID, current_user: User) -> StockImport:
        stock_import = self.db.query(StockImport).filter(StockImport.id == import_id, StockImport.store_id == current_user.store_id).first()
        if not stock_import:
            raise not_found("Stock import")
        return stock_import

    def preview(self, import_id: UUID, current_user: User) -> tuple[StockImport, list[StockImportRow]]:
        stock_import = self.get(import_id, current_user)
        rows = self.db.query(StockImportRow).filter(StockImportRow.stock_import_id == stock_import.id).order_by(StockImportRow.row_number).all()
        return stock_import, rows

    def list(self, current_user: User) -> list[StockImport]:
        return self.db.query(StockImport).filter(StockImport.store_id == current_user.store_id).order_by(StockImport.created_at.desc()).all()

    def confirm(self, import_id: UUID, current_user: User, request_id: str) -> StockImport:
        stock_import = self.get(import_id, current_user)
        if stock_import.status == COMPLETED:
            return stock_import
        if stock_import.status != READY:
            raise conflict("Only a validated opening-stock import can be confirmed", "IMPORT_NOT_READY")
        stock_import.status = "BACKUP_STARTED"
        self.db.commit()
        try:
            backup = self.backup_runner.run(stock_import)
            if not backup.path or backup.size_bytes <= 0 or len(backup.sha256) != 64:
                raise RuntimeError("The backup verification result is incomplete")
        except Exception:
            stock_import = self.get(import_id, current_user)
            stock_import.status = "BACKUP_FAILED"
            stock_import.failure_details = {"code": "BACKUP_FAILED", "message": "The verified backup did not complete; inventory was not changed."}
            self.db.commit()
            raise conflict("Verified backup failed; opening stock was not imported", "BACKUP_FAILED")
        stock_import = self.get(import_id, current_user)
        self.db.add(StockImportBackup(stock_import_id=stock_import.id, status="VERIFIED", backup_path=backup.path, sha256=backup.sha256, size_bytes=backup.size_bytes, backup_metadata=backup.metadata))
        stock_import.status = "COMMITTING"
        self.db.commit()
        try:
            self._commit_opening_stock(stock_import, current_user, request_id)
            self.db.commit()
        except Exception as exc:
            self.db.rollback()
            failed = self.get(import_id, current_user)
            failed.status = "FAILED"
            failed.failure_details = {"code": "COMMIT_FAILED", "message": "The import was rolled back before any opening stock was committed.", "error_type": type(exc).__name__}
            self.db.commit()
            raise
        return self.get(import_id, current_user)

    def _validate_upload(self, stock_import: StockImport, content: bytes) -> None:
        stock_import.status = "VALIDATING"
        try:
            rows = list(csv.DictReader(StringIO(content.decode("utf-8-sig"))))
        except UnicodeDecodeError as exc:
            stock_import.status = "VALIDATION_FAILED"
            stock_import.failure_details = {"code": "CSV_ENCODING_INVALID", "message": "The file must be UTF-8 CSV."}
            return
        required = {"sku", "barcode", "quantity"}
        if not rows or not required.issubset(set(rows[0])):
            stock_import.status = "VALIDATION_FAILED"
            stock_import.failure_details = {"code": "CSV_HEADERS_INVALID", "message": "CSV requires sku, barcode and quantity columns."}
            stock_import.summary = {"total_rows": len(rows), "valid_rows": 0, "invalid_rows": len(rows)}
            return
        seen_skus, seen_barcodes, errors = set(), set(), 0
        for row_number, raw in enumerate(rows, start=2):
            sku, barcode = (raw.get("sku") or "").strip() or None, (raw.get("barcode") or "").strip() or None
            row_errors: list[str] = []
            try: quantity = int((raw.get("quantity") or "").strip())
            except ValueError: quantity = None
            if not sku and not barcode: row_errors.append("SKU or barcode is required")
            if quantity is None or quantity <= 0: row_errors.append("Quantity must be a positive whole number")
            if sku and sku.casefold() in seen_skus: row_errors.append("Duplicate SKU in import file")
            if barcode and barcode.casefold() in seen_barcodes: row_errors.append("Duplicate barcode in import file")
            if sku: seen_skus.add(sku.casefold())
            if barcode: seen_barcodes.add(barcode.casefold())
            variant = self._resolve_variant(stock_import.store_id, sku, barcode)
            if not row_errors and variant is None: row_errors.append("No active exact store variant matches the supplied SKU/barcode")
            if variant is not None and self.db.query(StockHistory.id).filter(StockHistory.store_id == stock_import.store_id, StockHistory.product_variant_id == variant.id, StockHistory.movement_type == StockMovementType.OPENING_STOCK).first(): row_errors.append("Opening stock already exists for this variant")
            self.db.add(StockImportRow(stock_import_id=stock_import.id, row_number=row_number, sku=sku, barcode=barcode, quantity=quantity, product_id=variant.product_id if variant and not row_errors else None, product_variant_id=variant.id if variant and not row_errors else None, validation_errors=row_errors, normalized_data={"sku": sku, "barcode": barcode, "quantity": quantity}))
            errors += bool(row_errors)
        stock_import.summary = {"total_rows": len(rows), "valid_rows": len(rows) - errors, "invalid_rows": errors, "total_quantity": sum(int((row.get("quantity") or "0").strip() or 0) for row in rows if (row.get("quantity") or "").strip().isdigit())}
        stock_import.status = READY if errors == 0 else "VALIDATION_FAILED"
        stock_import.failure_details = {} if errors == 0 else {"code": "OPENING_STOCK_VALIDATION_FAILED", "message": "Fix every invalid row before creating a new import."}

    def _resolve_variant(self, store_id: UUID, sku: str | None, barcode: str | None) -> ProductVariant | None:
        query = self.db.query(ProductVariant).filter(ProductVariant.store_id == store_id, ProductVariant.is_active.is_(True))
        if sku and barcode:
            return query.filter(ProductVariant.internal_sku == sku, ProductVariant.barcode == barcode).first()
        if sku: return query.filter(ProductVariant.internal_sku == sku).first()
        return query.filter(ProductVariant.barcode == barcode).first()

    def _commit_opening_stock(self, stock_import: StockImport, current_user: User, request_id: str) -> None:
        locked = self.db.query(StockImport).filter(StockImport.id == stock_import.id, StockImport.store_id == current_user.store_id).with_for_update().one()
        if locked.status == COMPLETED: return
        if locked.status != "COMMITTING": raise RuntimeError("Import state changed before commit")
        rows = self.db.query(StockImportRow).filter(StockImportRow.stock_import_id == locked.id).order_by(StockImportRow.row_number).with_for_update().all()
        if any(row.validation_errors or not row.product_variant_id or not row.quantity for row in rows): raise RuntimeError("Validation rows are not commit-ready")
        for row in rows:
            variant = self.db.query(ProductVariant).filter(ProductVariant.id == row.product_variant_id, ProductVariant.store_id == locked.store_id, ProductVariant.is_active.is_(True)).with_for_update().one()
            product = self.db.query(Product).filter(Product.id == variant.product_id, Product.store_id == locked.store_id).with_for_update().one()
            inventory = self.db.query(ProductInventory).filter(ProductInventory.product_id == product.id, ProductInventory.store_id == locked.store_id).with_for_update().first()
            if inventory is None:
                inventory = ProductInventory(product_id=product.id, store_id=locked.store_id, current_stock=0, minimum_stock=product.minimum_stock)
                self.db.add(inventory); self.db.flush()
            if self.db.query(StockHistory.id).filter(StockHistory.store_id == locked.store_id, StockHistory.product_variant_id == variant.id, StockHistory.movement_type == StockMovementType.OPENING_STOCK).first(): raise RuntimeError("Opening stock already exists for a selected variant")
            before = variant.current_stock
            variant.current_stock += row.quantity
            product.current_stock += row.quantity
            inventory.current_stock += row.quantity
            movement = StockHistory(product_id=product.id, product_variant_id=variant.id, store_id=locked.store_id, movement_type=StockMovementType.OPENING_STOCK, qty=row.quantity, before_stock=before, after_stock=variant.current_stock, reference=f"opening-import:{locked.id}", request_id=request_id, created_by=current_user.id)
            self.db.add(movement); self.db.flush(); row.opening_stock_movement_id = movement.id
        locked.status = COMPLETED
        locked.confirmed_by = current_user.id
        locked.confirmed_at = datetime.now(timezone.utc)
        locked.failure_details = {}
