from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import bad_request, conflict, not_found
from app.models.opening_stock_import import OpeningStockImportRow
from app.models.product_barcode import ProductBarcode, ProductBarcodeAudit
from app.models.product_deletion_audit import ProductDeletionAudit
from app.models.product import Product
from app.models.product_variant import InventoryCostLot, ProductVariant
from app.models.purchase_item import PurchaseItem
from app.models.sale import SaleItem
from app.models.stock_audit_event import StockAuditEvent
from app.models.stock_history import StockHistory
from app.models.stock_import import StockImportRow
from app.models.stock_scan import StockScanSessionItem
from app.models.user import User
from app.models.enums import PricingType
from app.models.enums import UserRole
from app.schemas.product import ProductVariantDetailsCreate, ProductVariantUpdate
from app.services.product_service import ProductService


class VariantManagementService:
    """Safe, variant-scoped catalogue management with immutable audit snapshots."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def update(self, variant_id: UUID, payload: ProductVariantUpdate, current_user: User, request_id: str) -> ProductVariant:
        variant = self._variant(variant_id, current_user, lock=True)
        values = payload.model_dump(exclude_unset=True)
        before = self._snapshot(variant)
        barcode = values.get("barcode", variant.barcode)
        sku = values.get("internal_sku", variant.internal_sku)
        if not barcode:
            raise bad_request("Barcode is required for every variant.", "VARIANT_BARCODE_REQUIRED")
        if barcode.casefold() != variant.barcode.casefold() and current_user.role != UserRole.OWNER:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"message": "Only an owner can change a barcode assignment.", "code": "OWNER_BARCODE_MANAGEMENT_REQUIRED"})
        if not sku:
            raise bad_request("SKU is required for every variant.", "VARIANT_SKU_REQUIRED")
        self._validate_unique(variant, barcode, sku, values.get("size", variant.size), values.get("color", variant.color))
        for field, source in (("size", "size"), ("color", "color"), ("style_code", "style_code"), ("manufacturer_sku", "manufacturer_sku"), ("mrp", "mrp"), ("selling_price", "selling_price"), ("internal_sku", "internal_sku"), ("is_active", "is_active")):
            if source in values:
                setattr(variant, field, values[source])
        if "purchase_cost" in values:
            variant.last_purchase_cost = values["purchase_cost"]
        variant.identity_key = self._identity(variant)
        scan_unit = values.get("scan_unit", variant.scan_unit)
        pieces = values.get("pieces_per_pack", variant.pieces_per_pack)
        if scan_unit == "PIECE":
            pieces = 1
        elif pieces < 2:
            raise bad_request("Pieces per Pack must be at least 2 for Pack scans.", "PACK_QUANTITY_REQUIRED")
        self._sync_primary_mapping(variant, barcode, scan_unit, pieces, current_user, request_id)
        if values.get("is_active") is False:
            self._set_mapping_state(variant, False)
        elif values.get("is_active") is True:
            self._set_mapping_state(variant, True)
        # Include a newly created barcode mapping in the immutable after snapshot.
        self.db.flush()
        self.db.expire(variant, ["barcode_mappings"])
        self._audit(variant, current_user, request_id, "VARIANT_UPDATED", "UPDATE", before, self._snapshot(variant))
        self.db.commit()
        return self._variant(variant_id, current_user)

    def create_details(self, payload: ProductVariantDetailsCreate, current_user: User, request_id: str) -> ProductVariant:
        """Commit a reviewed product/variant/barcode mapping without inventory side effects."""
        if not current_user.store_id:
            raise not_found("Current store")
        try:
            product = self._existing_product(payload.product_id, current_user) if payload.product_id else self._new_product(payload, current_user)
            variant = ProductVariant(
                id=uuid4(),
                store_id=current_user.store_id,
                product_id=product.id,
                size=payload.size,
                color=payload.color,
                style_code=payload.style_code,
                manufacturer_sku=payload.manufacturer_sku,
                internal_sku=payload.internal_sku,
                barcode=payload.barcode,
                identity_key="pending",
                mrp=payload.mrp,
                selling_price=payload.selling_price,
                last_purchase_cost=payload.purchase_cost,
                average_cost=payload.purchase_cost,
                current_stock=0,
                is_active=True,
            )
            self._validate_unique(variant, payload.barcode, payload.internal_sku, payload.size, payload.color)
            variant.identity_key = self._identity(variant)
            self.db.add(variant)
            self.db.flush()
            mapping = ProductBarcode(
                store_id=current_user.store_id, product_id=product.id, product_variant_id=variant.id, barcode=payload.barcode,
                barcode_type="AUTO", manufacturer_barcode=True, package_quantity=payload.pieces_per_pack if payload.scan_unit == "PACK" else 1,
                scan_unit=payload.scan_unit, inventory_unit="PIECE", base_unit_conversion=payload.pieces_per_pack if payload.scan_unit == "PACK" else 1,
                sale_mode="PACK_ONLY" if payload.scan_unit == "PACK" else "PIECE_ONLY", mrp=payload.mrp, default_selling_price=payload.selling_price,
                active=True,
            )
            self.db.add(mapping)
            self.db.add(ProductBarcodeAudit(store_id=current_user.store_id, barcode=payload.barcode, old_product_variant_id=None, new_product_variant_id=variant.id, action="DETAILS_CONFIRMED", reason="MANAGEMENT_ADD_DETAILS", changed_by=current_user.id, request_id=request_id))
            self._audit(variant, current_user, request_id, "VARIANT_DETAILS_CREATED", "CREATE", {}, self._snapshot(variant))
            self.db.commit()
            return self._variant(variant.id, current_user)
        except Exception:
            self.db.rollback()
            raise

    def archive(self, variant_id: UUID, current_user: User, request_id: str, active: bool = False) -> ProductVariant:
        variant = self._variant(variant_id, current_user, lock=True)
        before = self._snapshot(variant)
        variant.is_active = active
        self._set_mapping_state(variant, active)
        self._audit(variant, current_user, request_id, "VARIANT_RESTORED" if active else "VARIANT_ARCHIVED", "ARCHIVE", before, self._snapshot(variant))
        self.db.commit()
        return self._variant(variant_id, current_user)

    def check_delete(self, variant_id: UUID, current_user: User, request_id: str) -> dict:
        variant = self._variant(variant_id, current_user)
        assessment = self._delete_assessment(variant)
        return {"variant_id": str(variant.id), "product_id": str(variant.product_id), "variant_label": self._label(variant), "can_delete": assessment["code"] is None, "reason": assessment["reason"], "code": assessment["code"], "references": assessment["references"], "request_id": request_id}

    def permanently_delete(self, variant_id: UUID, confirmation: str, current_user: User, request_id: str) -> dict:
        if confirmation != "DELETE VARIANT":
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"message": "Type DELETE VARIANT to confirm permanent deletion.", "code": "DELETE_CONFIRMATION_REQUIRED", "request_id": request_id})
        variant = self._variant(variant_id, current_user, lock=True)
        assessment = self._delete_assessment(variant)
        if assessment["code"]:
            self._audit(variant, current_user, request_id, "VARIANT_DELETE_BLOCKED", "PERMANENT_DELETE", self._snapshot(variant), {"reason": assessment["reason"], "references": assessment["references"]})
            self.db.commit()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"message": assessment["reason"], "code": assessment["code"], "references": assessment["references"], "request_id": request_id})
        snapshot = self._snapshot(variant)
        self._audit(variant, current_user, request_id, "VARIANT_PERMANENTLY_DELETED", "PERMANENT_DELETE", snapshot, {"deleted": True})
        self.db.query(ProductBarcode).filter(ProductBarcode.product_variant_id == variant.id).delete(synchronize_session=False)
        self.db.delete(variant)
        self.db.commit()
        return {"variant_id": str(variant_id), "deleted": True, "request_id": request_id}

    def _variant(self, variant_id: UUID, current_user: User, lock: bool = False) -> ProductVariant:
        if not current_user.store_id:
            raise not_found("Product variant")
        # Do not join the optional parent row in a FOR UPDATE query: PostgreSQL
        # rejects row locks on the nullable side of an outer join.
        query = self.db.query(ProductVariant).options(selectinload(ProductVariant.barcode_mappings)).filter(ProductVariant.id == variant_id, ProductVariant.store_id == current_user.store_id)
        if lock:
            query = query.with_for_update()
        variant = query.first()
        if not variant:
            raise not_found("Product variant")
        return variant

    def _validate_unique(self, variant: ProductVariant, barcode: str, sku: str, size: str | None, color: str | None) -> None:
        base = self.db.query(ProductVariant).filter(ProductVariant.store_id == variant.store_id)
        if variant.id:
            base = base.filter(ProductVariant.id != variant.id)
        if base.filter(func.lower(ProductVariant.barcode) == barcode.lower()).first():
            raise conflict("This barcode is already used by another variant.", "VARIANT_BARCODE_CONFLICT")
        barcode_query = self.db.query(ProductBarcode).filter(ProductBarcode.store_id == variant.store_id, func.lower(ProductBarcode.barcode) == barcode.lower())
        if variant.id:
            barcode_query = barcode_query.filter(ProductBarcode.product_variant_id != variant.id)
        if barcode_query.first():
            raise conflict("This barcode is already assigned to another variant.", "BARCODE_ALREADY_ASSIGNED")
        if base.filter(func.lower(ProductVariant.internal_sku) == sku.lower()).first():
            raise conflict("This SKU is already used by another variant.", "VARIANT_SKU_CONFLICT")
        duplicate = base.filter(ProductVariant.product_id == variant.product_id, func.coalesce(func.lower(ProductVariant.size), "") == (size or "").lower(), func.coalesce(func.lower(ProductVariant.color), "") == (color or "").lower(), func.coalesce(func.lower(ProductVariant.style_code), "") == (variant.style_code or "").lower()).first()
        if duplicate:
            raise self._duplicate_variant_error(duplicate)

    @staticmethod
    def _duplicate_variant_error(duplicate: ProductVariant) -> HTTPException:
        """Return a resolvable conflict instead of a dead-end validation error.

        The client can open the already-existing exact variant.  It must never
        silently merge the edited variant into that record: either record may
        have stock or an immutable sales/inventory history.
        """
        label = " / ".join(value for value in (duplicate.size, duplicate.color) if value) or "Standard"
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": f"{label} already exists for this product.",
                "code": "VARIANT_ALREADY_EXISTS",
                "existing_variant": {
                    "id": str(duplicate.id),
                    "size": duplicate.size,
                    "color": duplicate.color,
                    "current_stock": int(duplicate.current_stock or 0),
                    "is_active": duplicate.is_active,
                },
            },
        )

    def _existing_product(self, product_id: UUID | None, current_user: User) -> Product:
        product = self.db.query(Product).filter(Product.id == product_id, Product.store_id == current_user.store_id).with_for_update().first()
        if not product:
            raise not_found("Product")
        return product

    def _new_product(self, payload: ProductVariantDetailsCreate, current_user: User) -> Product:
        service = ProductService(self.db)
        service._ensure_hierarchy(payload.category_id, payload.subcategory_id, payload.brand_id)  # type: ignore[arg-type]
        service._validate_unique_product(payload.category_id, payload.subcategory_id, payload.brand_id, payload.product_name or "", store_id=current_user.store_id)  # type: ignore[arg-type]
        product = Product(
            store_id=current_user.store_id, category_id=payload.category_id, subcategory_id=payload.subcategory_id, brand_id=payload.brand_id,
            name=payload.product_name or "", sku=None, size=payload.size, color=payload.color, purchase_price=payload.purchase_cost,
            selling_price=payload.selling_price, pricing_type=PricingType.OWN_PRICE, mrp=payload.mrp, current_stock=0, minimum_stock=0,
            barcode=None, description=payload.description, unit="Each", is_active=True,
        )
        self.db.add(product)
        self.db.flush()
        return product

    def _sync_primary_mapping(self, variant: ProductVariant, barcode: str, scan_unit: str, pieces: int, current_user: User, request_id: str) -> None:
        current = next((item for item in variant.barcode_mappings if item.barcode.lower() == variant.barcode.lower()), None)
        if barcode.lower() != variant.barcode.lower():
            if current:
                current.active = False
                self.db.add(ProductBarcodeAudit(store_id=variant.store_id, barcode=current.barcode, old_product_variant_id=variant.id, new_product_variant_id=variant.id, action="VARIANT_BARCODE_REPLACED", reason="Variant barcode edited", changed_by=current_user.id, request_id=request_id))
            current = None
            variant.barcode = barcode
        mapping = next((item for item in variant.barcode_mappings if item.barcode.lower() == barcode.lower()), None) or current
        if not mapping:
            mapping = ProductBarcode(store_id=variant.store_id, product_id=variant.product_id, product_variant_id=variant.id, barcode=barcode, barcode_type="AUTO", manufacturer_barcode=True)
            self.db.add(mapping)
            self.db.add(ProductBarcodeAudit(store_id=variant.store_id, barcode=barcode, old_product_variant_id=None, new_product_variant_id=variant.id, action="VARIANT_BARCODE_ASSIGNED", reason="Variant configuration updated", changed_by=current_user.id, request_id=request_id))
        mapping.barcode = barcode
        mapping.package_quantity = pieces
        mapping.scan_unit = scan_unit
        mapping.inventory_unit = "PIECE"
        mapping.base_unit_conversion = pieces
        mapping.sale_mode = "PACK_ONLY" if scan_unit == "PACK" else "PIECE_ONLY"
        mapping.mrp = variant.mrp
        mapping.default_selling_price = variant.selling_price
        mapping.active = variant.is_active

    @staticmethod
    def _identity(variant: ProductVariant) -> str:
        return "|".join((str(variant.product_id), (variant.size or "").casefold(), (variant.color or "").casefold(), (variant.style_code or "").casefold(), str(variant.mrp or variant.selling_price), str(variant.selling_price), str(variant.id)))

    def _set_mapping_state(self, variant: ProductVariant, active: bool) -> None:
        for mapping in variant.barcode_mappings:
            mapping.active = active

    def _delete_assessment(self, variant: ProductVariant) -> dict:
        refs = {
            "physical_stock": int(variant.current_stock or 0),
            "stock_history": self.db.query(StockHistory).filter(StockHistory.product_variant_id == variant.id).count(),
            "sale_items": self.db.query(SaleItem).filter(SaleItem.product_variant_id == variant.id).count(),
            "purchase_items": self.db.query(PurchaseItem).filter(PurchaseItem.product_variant_id == variant.id).count(),
            "cost_lots": self.db.query(InventoryCostLot).filter(InventoryCostLot.product_variant_id == variant.id).count(),
            "stock_scan_items": self.db.query(StockScanSessionItem).filter(StockScanSessionItem.product_variant_id == variant.id).count(),
            "stock_import_rows": self.db.query(StockImportRow).filter(StockImportRow.product_variant_id == variant.id).count(),
            "opening_stock_rows": self.db.query(OpeningStockImportRow).filter(OpeningStockImportRow.product_variant_id == variant.id).count(),
            "stock_audit_events": self.db.query(StockAuditEvent).filter(StockAuditEvent.product_variant_id == variant.id).count(),
            "barcode_audits": self.db.query(ProductBarcodeAudit).filter(or_(ProductBarcodeAudit.old_product_variant_id == variant.id, ProductBarcodeAudit.new_product_variant_id == variant.id)).count(),
        }
        if refs["physical_stock"] > 0:
            return {"reason": f"This variant still has {refs['physical_stock']} units in stock. Adjust stock to zero before deletion.", "code": "VARIANT_HAS_STOCK", "references": refs}
        if sum(value for key, value in refs.items() if key != "physical_stock"):
            return {"reason": "This variant has inventory, barcode, purchase, or sale history and must be archived instead.", "code": "VARIANT_HAS_TRANSACTION_HISTORY", "references": refs}
        return {"reason": None, "code": None, "references": refs}

    def _audit(self, variant: ProductVariant, current_user: User, request_id: str, event_type: str, mode: str, before: dict, after: dict) -> None:
        self.db.add(ProductDeletionAudit(store_id=variant.store_id, product_id=variant.product_id, event_type=event_type, delete_mode=mode, reason=None, request_id=request_id, product_snapshot={"variant_id": str(variant.id), "before": before, "after": after}, deleted_record_counts={}, performed_by=current_user.id, performed_by_role=current_user.role.value))

    @staticmethod
    def _label(variant: ProductVariant) -> str:
        return " / ".join(value for value in (variant.size, variant.color, variant.internal_sku) if value) or variant.internal_sku

    @staticmethod
    def _snapshot(variant: ProductVariant) -> dict:
        return {"id": str(variant.id), "size": variant.size, "color": variant.color, "mrp": str(variant.mrp) if variant.mrp is not None else None, "selling_price": str(variant.selling_price), "purchase_cost": str(variant.last_purchase_cost), "barcode": variant.barcode, "internal_sku": variant.internal_sku, "scan_unit": variant.scan_unit, "pieces_per_pack": variant.pieces_per_pack, "is_active": variant.is_active}
