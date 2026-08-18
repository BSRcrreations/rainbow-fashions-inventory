from __future__ import annotations

"""One canonical interpretation of a barcode for every UAT-facing workflow."""

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import bad_request
from app.models.product import Product
from app.models.product_barcode import ProductBarcode, ProductBarcodeVariantTarget
from app.models.product_variant import ProductVariant
from app.models.user import User
from app.schemas.stock_scan import BarcodeLookupAssignmentRead, BarcodeLookupRead


class BarcodeResolutionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def lookup(self, barcode: str, current_user: User) -> BarcodeLookupRead:
        normalized = barcode.strip()
        if not normalized:
            raise bad_request("Barcode is required")
        if not current_user.store_id:
            raise bad_request("Current user is not assigned to an active store.", "STORE_SCOPE_REQUIRED")
        return self.lookup_for_store(normalized, current_user.store_id)

    def lookup_for_store(self, barcode: str, store_id: UUID) -> BarcodeLookupRead:
        normalized = barcode.strip()
        mapping = self.db.query(ProductBarcode).filter(
            ProductBarcode.store_id == store_id,
            func.lower(ProductBarcode.barcode) == normalized.casefold(),
        ).first()
        if mapping:
            if not mapping.active:
                # A deliberate unlink leaves an audit record but frees the barcode.
                return BarcodeLookupRead(barcode=normalized, status="AVAILABLE", message="Barcode Available", assignments=[])
            assignments = self._mapping_assignments(mapping, store_id)
            if not assignments:
                return BarcodeLookupRead(barcode=normalized, status="STALE", message="Old/inactive barcode assignment detected", assignments=[])
            if any(not assignment.active for assignment in assignments):
                return BarcodeLookupRead(barcode=normalized, status="STALE", message="Old/inactive barcode assignment detected", assignments=assignments)
            product_ids = {assignment.product_id for assignment in assignments}
            colours = {(assignment.color or "").casefold() for assignment in assignments}
            if len(product_ids) != 1 or len(colours) != 1:
                return BarcodeLookupRead(barcode=normalized, status="CONFLICT", message="Barcode is assigned to unrelated active variants", assignments=assignments)
            status = "SHARED" if len(assignments) > 1 else "UNIQUE"
            return BarcodeLookupRead(barcode=normalized, status=status, message="Shared barcode assignment" if status == "SHARED" else "Active barcode assignment", assignments=assignments)

        legacy = self._legacy_assignments(normalized, store_id)
        if not legacy:
            return BarcodeLookupRead(barcode=normalized, status="AVAILABLE", message="Barcode Available", assignments=[])
        active = [assignment for assignment in legacy if assignment.active]
        if not active:
            return BarcodeLookupRead(barcode=normalized, status="STALE", message="Old/inactive barcode assignment detected", assignments=legacy)
        product_ids = {assignment.product_id for assignment in active}
        colours = {(assignment.color or "").casefold() for assignment in active}
        if len(product_ids) != 1 or len(colours) != 1:
            return BarcodeLookupRead(barcode=normalized, status="CONFLICT", message="Barcode is assigned to unrelated active variants", assignments=active)
        status = "SHARED" if len(active) > 1 else "UNIQUE"
        return BarcodeLookupRead(barcode=normalized, status=status, message="Legacy barcode assignment" if status == "UNIQUE" else "Shared barcode assignment", assignments=active)

    def _mapping_assignments(self, mapping: ProductBarcode, store_id: UUID) -> list[BarcodeLookupAssignmentRead]:
        ids = [variant_id for (variant_id,) in self.db.query(ProductBarcodeVariantTarget.product_variant_id).filter(
            ProductBarcodeVariantTarget.product_barcode_id == mapping.id,
            ProductBarcodeVariantTarget.store_id == store_id,
        ).all()]
        if mapping.product_variant_id not in ids:
            ids.append(mapping.product_variant_id)
        return self._assignments_for_variants(ids, mapping.id, store_id)

    def _legacy_assignments(self, barcode: str, store_id: UUID) -> list[BarcodeLookupAssignmentRead]:
        variants = self.db.query(ProductVariant).filter(
            ProductVariant.store_id == store_id,
            func.lower(ProductVariant.barcode) == barcode.casefold(),
        ).all()
        return self._assignments_for_variants([variant.id for variant in variants], None, store_id)

    def _assignments_for_variants(self, variant_ids: list[UUID], barcode_id: UUID | None, store_id: UUID) -> list[BarcodeLookupAssignmentRead]:
        if not variant_ids:
            return []
        variants = self.db.query(ProductVariant).options(
            joinedload(ProductVariant.product).joinedload(Product.brand),
            joinedload(ProductVariant.product).joinedload(Product.category),
        ).filter(ProductVariant.store_id == store_id, ProductVariant.id.in_(variant_ids)).all()
        by_id = {variant.id: variant for variant in variants}
        result: list[BarcodeLookupAssignmentRead] = []
        for variant_id in variant_ids:
            variant = by_id.get(variant_id)
            if not variant:
                continue
            product = variant.product
            result.append(BarcodeLookupAssignmentRead(
                barcode_id=barcode_id or UUID(int=0), product_id=product.id, variant_id=variant.id,
                product_name=product.name, brand_name=product.brand.name if product.brand else None,
                category_name=product.category.name if product.category else None, size=variant.size,
                color=variant.color, current_stock=variant.current_stock,
                active=bool(variant.is_active and product.is_active),
            ))
        return result
