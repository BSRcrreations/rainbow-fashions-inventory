from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
import re
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.ai.base import OCRProcessingError
from app.ai.factory import get_ocr_service
from app.core.exceptions import bad_request, conflict, not_found
from app.models.brand import Brand
from app.models.category import Category
from app.models.enums import PricingType, PurchaseStatus, StockMovementType, StockScanMode, StockScanStatus, UserRole
from app.models.product import Product
from app.models.product_barcode import ProductBarcode, ProductBarcodeAudit
from app.models.product_inventory import ProductInventory
from app.models.product_variant import InventoryCostLot, ProductVariant
from app.models.purchase import Purchase
from app.models.purchase_item import PurchaseItem
from app.models.stock_history import StockHistory
from app.models.stock_scan import StockScanSession, StockScanSessionItem
from app.models.subcategory import SubCategory
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.stock_scan import (
    BarcodeAssignment,
    BarcodeImageResolutionRead,
    BarcodeOnboarding,
    BarcodeProductOnboarding,
    LabelExtractionSuggestion,
    ProductVariantBarcodeRead,
    StockScanConfirmRequest,
    StockScanItemUpdate,
    StockScanRequest,
    StockScanSessionCreate,
    StockScanSessionUpdate,
)
from app.services.file_service import FileService


class StockScanService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def resolve_barcode(self, barcode: str, current_user: User) -> ProductVariantBarcodeRead:
        normalized = barcode.strip()
        if not normalized:
            raise bad_request("Barcode is required")
        store_id = self._store_id(current_user)
        mapping = self._barcode_mapping(normalized, store_id)
        if mapping:
            variant = self.db.query(ProductVariant).options(joinedload(ProductVariant.product).joinedload(Product.category), joinedload(ProductVariant.product).joinedload(Product.brand)).filter(ProductVariant.id == mapping.product_variant_id, ProductVariant.store_id == store_id).first()
            if not variant or not variant.is_active or not variant.product.is_active:
                raise bad_request("This product variant is inactive.", "VARIANT_INACTIVE")
            return self._variant_read(variant, mapping)
        variant = (
            self.db.query(ProductVariant)
            .join(Product)
            .options(joinedload(ProductVariant.product).joinedload(Product.category), joinedload(ProductVariant.product).joinedload(Product.brand))
            .filter(ProductVariant.store_id == store_id, func.lower(ProductVariant.barcode) == normalized.lower())
            .first()
        )
        if not variant:
            raise bad_request("This barcode is not assigned to a product.", "BARCODE_NOT_FOUND")
        if not variant.is_active or not variant.product.is_active:
            raise bad_request("This product variant is inactive.", "VARIANT_INACTIVE")
        return self._variant_read(variant)

    def assign_barcode(self, variant_id: UUID, payload: BarcodeAssignment, current_user: User) -> ProductVariantBarcodeRead:
        return self.onboard_barcode(BarcodeOnboarding(product_variant_id=variant_id, barcode=payload.barcode), current_user)

    def remove_barcode(self, barcode_id: UUID, current_user: User, request_id: Optional[str] = None) -> None:
        store_id = self._store_id(current_user)
        mapping = self.db.query(ProductBarcode).filter(ProductBarcode.id == barcode_id, ProductBarcode.store_id == store_id).with_for_update().first()
        if not mapping:
            raise not_found("Barcode assignment")
        mapping.active = False
        self.db.add(ProductBarcodeAudit(store_id=store_id, barcode=mapping.barcode, old_product_variant_id=mapping.product_variant_id, new_product_variant_id=mapping.product_variant_id, action="REMOVED", reason="BARCODE_ONLY", changed_by=current_user.id, request_id=request_id))
        self.db.commit()

    def transfer_barcode(self, barcode_id: UUID, target_variant_id: UUID, current_user: User, request_id: Optional[str] = None) -> ProductVariantBarcodeRead:
        store_id = self._store_id(current_user)
        mapping = self.db.query(ProductBarcode).filter(ProductBarcode.id == barcode_id, ProductBarcode.store_id == store_id).with_for_update().first()
        if not mapping:
            raise not_found("Barcode assignment")
        target = self._variant_for_store(target_variant_id, store_id, lock=True)
        old_variant_id = mapping.product_variant_id
        mapping.product_variant_id = target.id
        mapping.product_id = target.product_id
        mapping.active = True
        self.db.add(ProductBarcodeAudit(store_id=store_id, barcode=mapping.barcode, old_product_variant_id=old_variant_id, new_product_variant_id=target.id, action="TRANSFERRED", reason="OWNER_CONFIRMED", changed_by=current_user.id, request_id=request_id))
        self.db.commit()
        return self._variant_read(target, mapping)

    def onboard_barcode(self, payload: BarcodeOnboarding, current_user: User, request_id: Optional[str] = None) -> ProductVariantBarcodeRead:
        store_id = self._store_id(current_user)
        barcode = payload.barcode.strip()
        self._validate_barcode(barcode)
        variant = (
            self.db.query(ProductVariant)
            .options(joinedload(ProductVariant.product).joinedload(Product.category), joinedload(ProductVariant.product).joinedload(Product.brand))
            .filter(ProductVariant.id == payload.product_variant_id, ProductVariant.store_id == store_id)
            .with_for_update()
            .first()
        )
        if not variant:
            raise not_found("Product variant")
        duplicate = self.db.query(ProductBarcode).filter(ProductBarcode.store_id == store_id, func.lower(ProductBarcode.barcode) == barcode.lower()).with_for_update().first()
        if duplicate:
            raise conflict(
                "This barcode is already assigned to another product variant.",
                "BARCODE_ALREADY_ASSIGNED",
            )
        mapping = ProductBarcode(
            store_id=store_id, product_id=variant.product_id, product_variant_id=variant.id, barcode=barcode,
            barcode_type=self._barcode_type(barcode, payload.barcode_type), manufacturer_barcode=payload.manufacturer_barcode,
            package_quantity=payload.package_quantity, scan_unit=payload.scan_unit.strip().upper(), inventory_unit=payload.inventory_unit.strip().upper(),
            base_unit_conversion=payload.package_quantity, sale_mode=payload.sale_mode.strip().upper(), mrp=variant.mrp, default_selling_price=payload.default_selling_price or variant.selling_price,
            verified=payload.verified, verified_by=current_user.id if payload.verified else None, verified_at=datetime.now(timezone.utc) if payload.verified else None,
        )
        self.db.add(mapping)
        self.db.add(ProductBarcodeAudit(store_id=store_id, barcode=barcode, old_product_variant_id=None, new_product_variant_id=variant.id, action="ASSIGNED", changed_by=current_user.id, request_id=request_id))
        if payload.package_quantity == 1:
            variant.barcode = barcode
        self.db.commit()
        self.db.refresh(variant)
        return self._variant_read(variant, mapping)

    def create_session(self, payload: StockScanSessionCreate, current_user: User) -> StockScanSession:
        store_id = self._store_id(current_user)
        self._validate_mode_configuration(payload.mode, payload.purchase_id, payload.location_name, payload.source_location_name, payload.destination_location_name, store_id)
        self._validate_session_defaults(payload.supplier_id, payload.default_category_id, payload.default_brand_id, payload.quick_post, current_user)
        session = StockScanSession(
            store_id=store_id,
            mode=payload.mode,
            status=StockScanStatus.IN_PROGRESS,
            quantity_mode=payload.quantity_mode,
            purchase_id=payload.purchase_id,
            supplier_id=payload.supplier_id,
            default_category_id=payload.default_category_id,
            default_brand_id=payload.default_brand_id,
            entry_date=payload.entry_date or date.today(),
            default_purchase_cost=payload.default_purchase_cost,
            default_selling_price=payload.default_selling_price,
            quick_post=payload.quick_post,
            location_name=payload.location_name,
            source_location_name=payload.source_location_name,
            destination_location_name=payload.destination_location_name,
            reference=payload.reference,
            notes=payload.notes,
            created_by=current_user.id,
        )
        self.db.add(session)
        self.db.commit()
        return self.get_session(session.id, current_user)

    def get_session(self, session_id: UUID, current_user: User) -> StockScanSession:
        session = self._session_query(current_user).filter(StockScanSession.id == session_id).first()
        if not session:
            raise not_found("Stock scan session")
        return session

    def update_session(self, session_id: UUID, payload: StockScanSessionUpdate, current_user: User) -> StockScanSession:
        session = self._editable_session(session_id, current_user)
        values = payload.model_dump(exclude_unset=True)
        for field, value in values.items():
            setattr(session, field, value)
        self._validate_mode_configuration(session.mode, session.purchase_id, session.location_name, session.source_location_name, session.destination_location_name, session.store_id)
        self._validate_session_defaults(session.supplier_id, session.default_category_id, session.default_brand_id, session.quick_post, current_user)
        self.db.commit()
        return self.get_session(session.id, current_user)

    async def resolve_label_image(self, file, current_user: User) -> BarcodeImageResolutionRead:
        """Persist a verified image and return conservative OCR suggestions for review."""
        uploaded = await FileService(self.db).save_product_image(file, current_user.id)
        image_url = f"/uploads/products/{uploaded.stored_filename}"
        try:
            text = get_ocr_service().extract_text(Path(uploaded.storage_path))
        except OCRProcessingError as exc:
            raise bad_request(exc.message, exc.code) from exc
        suggestions = self._label_suggestions(text)
        if not suggestions:
            raise bad_request(
                "The barcode could not be read from the image. Scan it again or enter the printed number.",
                "BARCODE_IMAGE_UNREADABLE",
            )
        return BarcodeImageResolutionRead(image_url=image_url, suggestions=suggestions)

    def onboard_product(self, payload: BarcodeProductOnboarding, current_user: User, request_id: Optional[str] = None) -> StockScanSession:
        """Atomically create/select a precise variant, map its barcode, and add it to a draft."""
        store_id = self._store_id(current_user)
        try:
            session = (
                self.db.query(StockScanSession)
                .filter(StockScanSession.id == payload.session_id, StockScanSession.store_id == store_id)
                .with_for_update()
                .first()
            )
            if not session:
                raise not_found("Stock scan session")
            if session.status == StockScanStatus.CONFIRMED:
                raise conflict("This stock session is confirmed and cannot be changed.", "STOCK_SESSION_CONFIRMED")
            if session.status == StockScanStatus.CANCELLED:
                raise bad_request("This stock-entry session has been cancelled")
            if session.mode == StockScanMode.PURCHASE_RECEIVING and payload.action != "EXISTING_VARIANT":
                raise bad_request("New products must be added to the purchase before they can be received.", "PURCHASE_BARCODE_MISMATCH")

            barcode = payload.barcode.strip()
            self._validate_barcode(barcode)
            if payload.action == "EXISTING_VARIANT":
                variant = self._variant_for_store(payload.product_variant_id, store_id, lock=True)
                mapping = self._barcode_mapping(barcode, store_id, lock=True, include_inactive=True)
                if mapping and mapping.product_variant_id != variant.id:
                    raise conflict("This barcode is already assigned to another product variant.", "BARCODE_ALREADY_ASSIGNED")
                if not mapping:
                    mapping = ProductBarcode(
                        store_id=store_id,
                        product_id=variant.product_id,
                        product_variant_id=variant.id,
                        barcode=barcode,
                        barcode_type=self._barcode_type(barcode, "AUTO"),
                        manufacturer_barcode=True,
                        package_quantity=1,
                        scan_unit="PIECE",
                        inventory_unit="PIECE",
                        base_unit_conversion=1,
                        sale_mode="PIECE_ONLY",
                        mrp=variant.mrp,
                        default_selling_price=variant.selling_price,
                        active=True,
                        verified=True,
                        verified_by=current_user.id,
                        verified_at=datetime.now(timezone.utc),
                    )
                    self.db.add(mapping)
                    self.db.flush()
                    self.db.add(ProductBarcodeAudit(
                        store_id=store_id,
                        barcode=barcode,
                        old_product_variant_id=None,
                        new_product_variant_id=variant.id,
                        action="ASSIGNED",
                        reason="EXISTING_VARIANT",
                        changed_by=current_user.id,
                        request_id=request_id,
                    ))
                elif not mapping.active:
                    mapping.active = True

                self._add_mapping_to_session(
                    session,
                    mapping,
                    variant,
                    payload.quantity,
                    variant.last_purchase_cost,
                    "SELLABLE",
                )
                self.db.commit()
                return self.get_session(session.id, current_user)

            duplicate = self._barcode_mapping(barcode, store_id, lock=True, include_inactive=True)
            if duplicate:
                raise conflict("This barcode is already assigned to another product variant.", "BARCODE_ALREADY_ASSIGNED")

            # The schema requires these values for new variants/products. Keep the
            # assertion here so the existing-variant branch can intentionally omit
            # all price and product metadata.
            assert payload.purchase_cost is not None
            assert payload.selling_price is not None

            if payload.action == "NEW_VARIANT":
                product = self._product_for_store(payload.existing_product_id, store_id, lock=True)
                variant = self._create_variant(product, payload, barcode, store_id)
                self.db.add(variant)
                self.db.flush()
            else:
                product = self._create_product(payload, store_id, session)
                self.db.add(product)
                self.db.flush()
                variant = self._create_variant(product, payload, barcode, store_id)
                self.db.add(variant)
                self.db.flush()

            mapping = ProductBarcode(
                store_id=store_id,
                product_id=variant.product_id,
                product_variant_id=variant.id,
                barcode=barcode,
                barcode_type=self._barcode_type(barcode, "AUTO"),
                manufacturer_barcode=True,
                package_quantity=payload.package_quantity,
                scan_unit=payload.scan_unit,
                inventory_unit=payload.inventory_unit.upper(),
                base_unit_conversion=payload.package_quantity,
                sale_mode=payload.sale_mode,
                mrp=payload.mrp if payload.mrp is not None else variant.mrp,
                default_selling_price=payload.selling_price,
                active=True,
                verified=True,
                verified_by=current_user.id,
                verified_at=datetime.now(timezone.utc),
            )
            self.db.add(mapping)
            self.db.flush()
            self._add_optional_barcode_mappings(payload, variant, store_id, current_user, request_id)
            if payload.package_quantity == 1:
                variant.barcode = barcode
            variant.mrp = payload.mrp if payload.mrp is not None else variant.mrp
            variant.selling_price = payload.selling_price
            variant.last_purchase_cost = payload.purchase_cost
            if variant.average_cost == 0:
                variant.average_cost = payload.purchase_cost
            self.db.add(ProductBarcodeAudit(
                store_id=store_id,
                barcode=barcode,
                old_product_variant_id=None,
                new_product_variant_id=variant.id,
                action="ONBOARDED",
                reason=payload.action,
                changed_by=current_user.id,
                request_id=request_id,
            ))
            self._add_mapping_to_session(session, mapping, variant, payload.quantity, payload.purchase_cost, payload.condition)
            self.db.commit()
            return self.get_session(session.id, current_user)
        except Exception:
            self.db.rollback()
            raise

    def scan(self, session_id: UUID, payload: StockScanRequest, current_user: User) -> StockScanSession:
        session = self._editable_session(session_id, current_user)
        mapping = self._barcode_mapping(payload.barcode, session.store_id, lock=True)
        variant = self._locked_variant_by_barcode(payload.barcode, session.store_id) if not mapping else self.db.query(ProductVariant).options(joinedload(ProductVariant.product)).filter(ProductVariant.id == mapping.product_variant_id).with_for_update(of=ProductVariant).first()
        if not variant:
            raise bad_request("This barcode is not assigned to a product.", "BARCODE_NOT_FOUND")
        if not variant.is_active or not variant.product.is_active:
            raise bad_request("This product variant is inactive.", "VARIANT_INACTIVE")
        expected = self._expected_quantity(session, variant.id)
        package_quantity = mapping.base_unit_conversion if mapping else 1
        item_query = self.db.query(StockScanSessionItem).filter(StockScanSessionItem.session_id == session.id)
        if mapping:
            item_query = item_query.filter(StockScanSessionItem.product_barcode_id == mapping.id)
        else:
            item_query = item_query.filter(
                StockScanSessionItem.product_variant_id == variant.id,
                StockScanSessionItem.barcode == variant.barcode,
            )
        item = item_query.with_for_update().first()
        if item:
            item.scanned_quantity += payload.quantity
            item.base_quantity = self._base_quantity(item.scanned_quantity, item.package_quantity)
            item.last_scanned_at = datetime.now(timezone.utc)
        else:
            item = StockScanSessionItem(
                session_id=session.id,
                product_id=variant.product_id,
                product_variant_id=variant.id,
                product_barcode_id=mapping.id if mapping else None,
                barcode=mapping.barcode if mapping else variant.barcode,
                scanned_quantity=payload.quantity,
                package_quantity=package_quantity,
                base_quantity=self._base_quantity(payload.quantity, package_quantity),
                expected_quantity=expected,
                unit_cost=variant.average_cost,
                condition="SELLABLE",
            )
            self.db.add(item)
        item.difference_quantity = self._difference(session.mode, item.base_quantity, item.expected_quantity)
        session.status = StockScanStatus.IN_PROGRESS
        self.db.commit()
        return self.get_session(session.id, current_user)

    def update_item(self, session_id: UUID, item_id: UUID, payload: StockScanItemUpdate, current_user: User) -> StockScanSession:
        session = self._editable_session(session_id, current_user)
        item = (
            self.db.query(StockScanSessionItem)
            .filter(StockScanSessionItem.id == item_id, StockScanSessionItem.session_id == session.id)
            .with_for_update()
            .first()
        )
        if not item:
            raise not_found("Stock scan item")
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        item.base_quantity = self._base_quantity(item.scanned_quantity, item.package_quantity)
        item.difference_quantity = self._difference(session.mode, item.base_quantity, item.expected_quantity)
        item.last_scanned_at = datetime.now(timezone.utc)
        self.db.commit()
        return self.get_session(session.id, current_user)

    def delete_item(self, session_id: UUID, item_id: UUID, current_user: User) -> None:
        session = self._editable_session(session_id, current_user)
        item = self.db.query(StockScanSessionItem).filter(StockScanSessionItem.id == item_id, StockScanSessionItem.session_id == session.id).first()
        if not item:
            raise not_found("Stock scan item")
        self.db.delete(item)
        self.db.commit()

    def validate(self, session_id: UUID, current_user: User) -> tuple[bool, list[str], StockScanSession]:
        session = self.get_session(session_id, current_user)
        messages = self._validation_messages(session)
        return not messages, messages, session

    def cancel(self, session_id: UUID, current_user: User) -> StockScanSession:
        session = self._editable_session(session_id, current_user)
        session.status = StockScanStatus.CANCELLED
        self.db.commit()
        return self.get_session(session.id, current_user)

    def delete_session(self, session_id: UUID, current_user: User) -> None:
        """Draft scan rows have no confirmed inventory effect and may be discarded."""
        session = self._editable_session(session_id, current_user)
        self.db.delete(session)
        self.db.commit()

    def correction_target(self, session_id: UUID, item_id: UUID, current_user: User) -> StockHistory:
        """Locate the immutable movement created for a confirmed scan row."""
        session = self.get_session(session_id, current_user)
        if session.status != StockScanStatus.CONFIRMED:
            raise bad_request("Only confirmed stock sessions can be corrected")
        item = next((candidate for candidate in session.items if candidate.id == item_id), None)
        if not item:
            raise not_found("Stock scan item")
        reference = session.reference or f"SCAN-{session.id}"
        movement = (
            self.db.query(StockHistory)
            .filter(
                StockHistory.store_id == session.store_id,
                StockHistory.product_variant_id == item.product_variant_id,
                StockHistory.reference == reference,
            )
            .order_by(StockHistory.created_at.desc())
            .first()
        )
        if not movement:
            raise not_found("Confirmed stock transaction")
        return movement

    def confirm(self, session_id: UUID, payload: StockScanConfirmRequest, current_user: User) -> StockScanSession:
        store_id = self._store_id(current_user)
        session = (
            self.db.query(StockScanSession)
            .filter(StockScanSession.id == session_id, StockScanSession.store_id == store_id)
            .with_for_update()
            .first()
        )
        if not session:
            raise not_found("Stock scan session")
        if session.status == StockScanStatus.CONFIRMED:
            raise conflict("This scan session has already been confirmed.")
        if session.status == StockScanStatus.CANCELLED:
            raise bad_request("Cancelled scan sessions cannot be confirmed")
        session = self.get_session(session.id, current_user)
        messages = self._validation_messages(session)
        if messages:
            raise bad_request("; ".join(messages), "SCAN_SESSION_INVALID")
        if payload.reference is not None:
            session.reference = payload.reference.strip() or None
        if payload.notes is not None:
            session.notes = payload.notes.strip() or None
        reference = session.reference or f"SCAN-{session.id}"

        if session.mode == StockScanMode.PURCHASE_RECEIVING:
            self._confirm_purchase_receipt(session, current_user)
        elif session.mode == StockScanMode.STOCK_TRANSFER:
            raise bad_request("Stock transfer requires location-level inventory, which is not configured for this store.", "LOCATION_INVENTORY_REQUIRED")
        else:
            for line in session.items:
                delta, movement_type = self._movement_for_line(session, line)
                if delta:
                    self._apply_variant_delta(line, delta, movement_type, reference, current_user)

        session.status = StockScanStatus.CONFIRMED
        session.confirmed_by = current_user.id
        session.confirmed_at = datetime.now(timezone.utc)
        self.db.commit()
        return self.get_session(session.id, current_user)

    def _confirm_purchase_receipt(self, session: StockScanSession, current_user: User) -> None:
        purchase = self._purchase(session.purchase_id, session.store_id)
        if purchase.status == PurchaseStatus.CONFIRMED:
            raise bad_request("This purchase has already been confirmed and received")
        purchase_items = {item.product_variant_id: item for item in purchase.items if item.product_variant_id}
        for line in session.items:
            purchase_item = purchase_items.get(line.product_variant_id)
            if not purchase_item:
                raise bad_request("This barcode is not part of the selected purchase.", "PURCHASE_BARCODE_MISMATCH")
            purchase_item.accepted_quantity = Decimal(line.base_quantity)
        # Purchase confirmation remains the single stock-entry point for supplier receipts.
        purchase.received_date = purchase.received_date or datetime.now(timezone.utc).date()

    def _movement_for_line(self, session: StockScanSession, line: StockScanSessionItem) -> tuple[int, StockMovementType]:
        if session.mode == StockScanMode.OPENING_STOCK:
            return line.base_quantity, StockMovementType.OPENING_STOCK
        if session.mode == StockScanMode.PHYSICAL_COUNT:
            difference = line.base_quantity - (line.expected_quantity or 0)
            return difference, StockMovementType.STOCK_COUNT_IN if difference > 0 else StockMovementType.STOCK_COUNT_OUT
        if session.mode == StockScanMode.STOCK_ADJUSTMENT:
            # The review quantity is the signed correction relative to the session snapshot.
            difference = line.base_quantity - (line.expected_quantity or 0)
            return difference, StockMovementType.MANUAL_ADJUSTMENT
        raise bad_request("This scan mode cannot create inventory movements")

    def _apply_variant_delta(self, line: StockScanSessionItem, delta: int, movement_type: StockMovementType, reference: str, current_user: User) -> None:
        variant = (
            self.db.query(ProductVariant)
            .options(joinedload(ProductVariant.product))
            .filter(ProductVariant.id == line.product_variant_id, ProductVariant.store_id == self._store_id(current_user))
            .with_for_update(of=ProductVariant)
            .first()
        )
        if not variant:
            raise bad_request("A scanned variant is no longer available in this store")
        product = variant.product
        before = variant.current_stock
        after = before + delta
        if after < 0:
            raise bad_request(f"{product.name} only has {before} units available; the count would make stock negative.")
        inventory = self._locked_inventory(product.id, variant.store_id)
        if inventory.current_stock + delta < 0:
            raise bad_request(f"{product.name} cannot have negative store inventory")

        unit_cost = line.unit_cost if line.unit_cost is not None else variant.average_cost
        cost_lot_id: Optional[UUID] = None
        if delta > 0:
            lot = InventoryCostLot(
                store_id=variant.store_id,
                product_variant_id=variant.id,
                received_quantity=delta,
                remaining_quantity=delta,
                unit_purchase_cost=unit_cost,
                allocated_landed_cost=Decimal("0"),
                effective_unit_cost=unit_cost,
                lot_reference=reference,
            )
            self.db.add(lot)
            self.db.flush()
            cost_lot_id = lot.id
            total_before_cost = variant.average_cost * before
            variant.average_cost = (total_before_cost + unit_cost * delta) / after if after else Decimal("0")
            variant.last_purchase_cost = unit_cost
        else:
            self._consume_cost_lots(variant.id, -delta)

        variant.current_stock = after
        product.current_stock += delta
        inventory.current_stock += delta
        self.db.add(StockHistory(
            product_id=product.id,
            product_variant_id=variant.id,
            purchase_cost_lot_id=cost_lot_id,
            unit_cost=unit_cost,
            store_id=variant.store_id,
            movement_type=movement_type,
            qty=abs(delta),
            before_stock=before,
            after_stock=after,
            reference=reference,
            created_by=current_user.id,
        ))

    def _consume_cost_lots(self, variant_id: UUID, quantity: int) -> None:
        remaining = quantity
        lots = (
            self.db.query(InventoryCostLot)
            .filter(InventoryCostLot.product_variant_id == variant_id, InventoryCostLot.remaining_quantity > 0)
            .order_by(InventoryCostLot.received_date, InventoryCostLot.created_at, InventoryCostLot.id)
            .with_for_update()
            .all()
        )
        for lot in lots:
            consumed = min(remaining, lot.remaining_quantity)
            lot.remaining_quantity -= consumed
            remaining -= consumed
            if not remaining:
                return
        # Legacy data can have no cost lots. Inventory is still adjusted, keeping the ledger append-only.

    def _expected_quantity(self, session: StockScanSession, variant_id: UUID) -> Optional[int]:
        if session.mode == StockScanMode.PURCHASE_RECEIVING:
            purchase = self._purchase(session.purchase_id, session.store_id)
            purchase_item = next((item for item in purchase.items if item.product_variant_id == variant_id), None)
            if not purchase_item:
                raise bad_request("This barcode is not part of the selected purchase.", "PURCHASE_BARCODE_MISMATCH")
            return int(purchase_item.quantity)
        variant = self.db.query(ProductVariant.current_stock).filter(ProductVariant.id == variant_id).scalar()
        return int(variant or 0)

    def _add_mapping_to_session(
        self,
        session: StockScanSession,
        mapping: ProductBarcode,
        variant: ProductVariant,
        quantity: int,
        unit_cost: Decimal,
        condition: str,
    ) -> StockScanSessionItem:
        expected = self._expected_quantity(session, variant.id)
        item = (
            self.db.query(StockScanSessionItem)
            .filter(StockScanSessionItem.session_id == session.id, StockScanSessionItem.barcode == mapping.barcode)
            .with_for_update()
            .first()
        )
        if item:
            item.scanned_quantity += quantity
            item.unit_cost = unit_cost
            item.condition = condition
            item.last_scanned_at = datetime.now(timezone.utc)
        else:
            item = StockScanSessionItem(
                session_id=session.id,
                product_id=variant.product_id,
                product_variant_id=variant.id,
                product_barcode_id=mapping.id,
                barcode=mapping.barcode,
                scanned_quantity=quantity,
                package_quantity=mapping.base_unit_conversion,
                expected_quantity=expected,
                unit_cost=unit_cost,
                condition=condition,
            )
            self.db.add(item)
        item.base_quantity = self._base_quantity(item.scanned_quantity, item.package_quantity)
        item.difference_quantity = self._difference(session.mode, item.base_quantity, item.expected_quantity)
        session.status = StockScanStatus.IN_PROGRESS
        return item

    def _product_for_store(self, product_id: Optional[UUID], store_id: UUID, lock: bool = False) -> Product:
        if not product_id:
            raise bad_request("Select an existing product")
        query = self.db.query(Product).filter(Product.id == product_id, Product.store_id == store_id)
        product = query.with_for_update().first() if lock else query.first()
        if not product:
            raise not_found("Product")
        return product

    def _variant_for_store(self, variant_id: Optional[UUID], store_id: UUID, lock: bool = False) -> ProductVariant:
        if not variant_id:
            raise bad_request("Select an existing variant")
        query = (
            self.db.query(ProductVariant)
            .join(Product, Product.id == ProductVariant.product_id)
            .options(joinedload(ProductVariant.product))
            .filter(
                ProductVariant.id == variant_id,
                ProductVariant.store_id == store_id,
                ProductVariant.is_active.is_(True),
                Product.is_active.is_(True),
            )
        )
        variant = query.with_for_update().first() if lock else query.first()
        if not variant:
            raise not_found("Product variant")
        return variant

    def _create_product(self, payload: BarcodeProductOnboarding, store_id: UUID, session: StockScanSession) -> Product:
        if not payload.category_id:
            raise bad_request("Select a category", "CATEGORY_REQUIRED")
        if not payload.brand_id:
            raise bad_request("Select a brand or choose Unbranded.", "BRAND_REQUIRED")
        category = self.db.query(Category).filter(Category.id == payload.category_id, Category.store_id == store_id, Category.is_active.is_(True)).first()
        if not category:
            raise not_found("Category")
        brand = self.db.query(Brand).filter(Brand.id == payload.brand_id, Brand.category_id == category.id, Brand.store_id == store_id, Brand.is_active.is_(True)).first()
        if not brand:
            raise bad_request("Brand does not belong to the selected category", "BRAND_CATEGORY_MISMATCH")
        subcategory = None
        if payload.subcategory_id:
            subcategory = self.db.query(SubCategory).filter(SubCategory.id == payload.subcategory_id, SubCategory.category_id == category.id, SubCategory.store_id == store_id, SubCategory.is_active.is_(True)).first()
            if not subcategory:
                raise bad_request("Subcategory does not belong to the selected category", "SUBCATEGORY_CATEGORY_MISMATCH")
        if not subcategory:
            subcategory = self.db.query(SubCategory).filter(SubCategory.category_id == category.id, SubCategory.store_id == store_id, SubCategory.is_active.is_(True)).order_by(SubCategory.name).first()
        if not subcategory:
            raise bad_request("Create a subcategory for the selected category before creating this product.", "SUBCATEGORY_REQUIRED")
        duplicate = self.db.query(Product).filter(
            Product.store_id == store_id,
            Product.category_id == category.id,
            Product.subcategory_id == subcategory.id,
            Product.brand_id == brand.id,
            func.lower(Product.name) == payload.product_name.strip().lower(),
        ).first()
        if duplicate:
            raise conflict("A product with this category, subcategory, brand, and name already exists.", "PRODUCT_DUPLICATE")
        return Product(
            store_id=store_id,
            category_id=category.id,
            subcategory_id=subcategory.id,
            brand_id=brand.id,
            sku=payload.product_code or None,
            name=payload.product_name.strip(),
            size=payload.size or None,
            color=payload.color or None,
            purchase_price=payload.purchase_cost,
            selling_price=payload.selling_price,
            pricing_type=payload.pricing_type,
            mrp=payload.mrp,
            current_stock=0,
            minimum_stock=payload.minimum_stock,
            barcode=None,
            product_date=payload.product_date or session.entry_date or date.today(),
            description=payload.description or None,
            hsn_sac=payload.hsn_sac or None,
            unit=payload.inventory_unit.title(),
            warehouse=session.location_name,
            image_url=payload.image_url or None,
            is_active=True,
            is_test_data=False,
        )

    def _add_optional_barcode_mappings(
        self,
        payload: BarcodeProductOnboarding,
        variant: ProductVariant,
        store_id: UUID,
        current_user: User,
        request_id: Optional[str],
    ) -> None:
        extra_barcodes = (
            (payload.alternate_barcode, "ALTERNATE", 1, "PIECE"),
            (payload.package_barcode, "PACKAGE", payload.package_barcode_quantity, "PACK"),
        )
        for raw_barcode, barcode_type, package_quantity, scan_unit in extra_barcodes:
            if not raw_barcode:
                continue
            barcode = raw_barcode.strip()
            self._validate_barcode(barcode)
            if self._barcode_mapping(barcode, store_id, lock=True):
                raise conflict("This barcode is already assigned to another product variant.", "BARCODE_ALREADY_ASSIGNED")
            self.db.add(ProductBarcode(
                store_id=store_id,
                product_id=variant.product_id,
                product_variant_id=variant.id,
                barcode=barcode,
                barcode_type=barcode_type,
                manufacturer_barcode=False,
                package_quantity=package_quantity,
                scan_unit=scan_unit,
                inventory_unit=payload.inventory_unit.upper(),
                base_unit_conversion=package_quantity,
                sale_mode=payload.sale_mode,
                mrp=payload.mrp if payload.mrp is not None else variant.mrp,
                default_selling_price=payload.selling_price,
                active=True,
                verified=True,
                verified_by=current_user.id,
                verified_at=datetime.now(timezone.utc),
            ))
            self.db.add(ProductBarcodeAudit(
                store_id=store_id,
                barcode=barcode,
                old_product_variant_id=None,
                new_product_variant_id=variant.id,
                action="ONBOARDED_OPTIONAL",
                reason=barcode_type,
                changed_by=current_user.id,
                request_id=request_id,
            ))

    @staticmethod
    def _create_variant(product: Product, payload: BarcodeProductOnboarding, barcode: str, store_id: UUID) -> ProductVariant:
        internal_sku = payload.internal_sku or f"RFV-{uuid4().hex[:12].upper()}"
        identity = "|".join((
            str(product.id),
            (payload.size or "").casefold(),
            (payload.color or "").casefold(),
            (payload.style_code or "").casefold(),
            (payload.model_number or "").casefold(),
            (payload.manufacturer_sku or "").casefold(),
            str(payload.mrp if payload.mrp is not None else payload.selling_price),
            str(payload.selling_price),
            barcode.casefold(),
        ))
        return ProductVariant(
            store_id=store_id,
            product_id=product.id,
            color=payload.color or None,
            size=payload.size or None,
            style_code=payload.style_code or None,
            model_number=payload.model_number or None,
            manufacturer_sku=payload.manufacturer_sku or None,
            internal_sku=internal_sku,
            barcode=barcode,
            identity_key=identity,
            mrp=payload.mrp,
            selling_price=payload.selling_price,
            last_purchase_cost=payload.purchase_cost,
            average_cost=payload.purchase_cost,
            current_stock=0,
            is_active=True,
        )

    def _validate_session_defaults(
        self,
        supplier_id: Optional[UUID],
        category_id: Optional[UUID],
        brand_id: Optional[UUID],
        quick_post: bool,
        current_user: User,
    ) -> None:
        store_id = self._store_id(current_user)
        if quick_post and current_user.role != UserRole.OWNER:
            from app.core.exceptions import forbidden

            raise forbidden("Only an owner can enable Quick Post")
        if supplier_id and not self.db.query(Supplier.id).filter(Supplier.id == supplier_id, Supplier.store_id == store_id).scalar():
            raise not_found("Supplier")
        if category_id and not self.db.query(Category.id).filter(Category.id == category_id, Category.store_id == store_id).scalar():
            raise not_found("Category")
        if brand_id:
            brand = self.db.query(Brand).filter(Brand.id == brand_id, Brand.store_id == store_id).first()
            if not brand:
                raise not_found("Brand")
            if category_id and brand.category_id != category_id:
                raise bad_request("Brand does not belong to the selected category", "BRAND_CATEGORY_MISMATCH")

    def _label_suggestions(self, text: str) -> dict[str, LabelExtractionSuggestion]:
        """Only suggest values visibly present in OCR text; never fabricate a label field."""
        source = " ".join(text.split())
        suggestions: dict[str, LabelExtractionSuggestion] = {}

        def add(name: str, value: str, confidence: float) -> None:
            if value:
                suggestions[name] = LabelExtractionSuggestion(value=value.strip(), confidence=confidence, source_text=source, requires_review=True)

        for candidate in re.findall(r"(?<!\d)(\d{8}|\d{12}|\d{13})(?!\d)", source):
            try:
                self._validate_barcode(candidate)
            except Exception:
                continue
            add("barcode", candidate, 0.9)
            break
        patterns = {
            "mrp": r"(?:M\.?R\.?P\.?|MRP)[^0-9]{0,12}([0-9]+(?:\.[0-9]{1,2})?)",
            "size": r"(?:SIZE|SZ)\s*[:.-]?\s*([A-Z0-9/ -]{1,20})",
            "color": r"(?:COLOU?R|CLR)\s*[:.-]?\s*([A-Z][A-Z /-]{1,24})",
            "style_code": r"(?:STYLE|MODEL|CODE)\s*(?:NO\.?|#)?\s*[:.-]?\s*([A-Z0-9/-]{2,40})",
            "hsn_sac": r"(?:HSN|SAC)\s*[:.-]?\s*([0-9A-Z/-]{4,20})",
            "package_quantity": r"(?:PACK\s*(?:OF)?|QTY\s*[:.-]?)\s*([0-9]{1,5})",
        }
        for name, pattern in patterns.items():
            match = re.search(pattern, source, re.IGNORECASE)
            if match:
                add(name, match.group(1), 0.76 if name != "mrp" else 0.84)
        return suggestions

    @staticmethod
    def _difference(mode: StockScanMode, scanned: int, expected: Optional[int]) -> Optional[int]:
        if mode in {StockScanMode.PHYSICAL_COUNT, StockScanMode.PURCHASE_RECEIVING, StockScanMode.STOCK_ADJUSTMENT}:
            return scanned - (expected or 0)
        return scanned

    @staticmethod
    def _base_quantity(scanned_quantity: int, package_quantity: int) -> int:
        return scanned_quantity * package_quantity

    def _validation_messages(self, session: StockScanSession) -> list[str]:
        messages: list[str] = []
        if not session.location_name.strip():
            messages.append("A warehouse or location is required")
        if not session.items:
            messages.append("Scan at least one product before confirmation")
        if any(item.scanned_quantity < 0 for item in session.items):
            messages.append("Scanned quantities cannot be negative")
        if session.mode == StockScanMode.PURCHASE_RECEIVING:
            if not session.purchase_id:
                messages.append("Select a purchase before receiving stock")
            else:
                self._purchase(session.purchase_id, session.store_id)
        if session.mode == StockScanMode.STOCK_TRANSFER:
            messages.append("Stock transfer requires configured location-level inventory")
        return messages

    def _validate_mode_configuration(self, mode: StockScanMode, purchase_id: Optional[UUID], location_name: str, source: Optional[str], destination: Optional[str], store_id: UUID) -> None:
        if not location_name.strip():
            raise bad_request("A warehouse or location is required")
        if mode == StockScanMode.PURCHASE_RECEIVING and not purchase_id:
            raise bad_request("Select a purchase before receiving stock")
        if purchase_id:
            self._purchase(purchase_id, store_id)
        if mode == StockScanMode.STOCK_TRANSFER:
            if not source or not destination:
                raise bad_request("Source and destination locations are required for transfers")
            if source.strip().casefold() == destination.strip().casefold():
                raise bad_request("Source and destination locations must be different")

    def _purchase(self, purchase_id: Optional[UUID], store_id: UUID) -> Purchase:
        if not purchase_id:
            raise bad_request("Select a purchase before receiving stock")
        purchase = self.db.query(Purchase).options(selectinload(Purchase.items)).filter(Purchase.id == purchase_id, Purchase.store_id == store_id).first()
        if not purchase:
            raise not_found("Purchase")
        return purchase

    def _editable_session(self, session_id: UUID, current_user: User) -> StockScanSession:
        session = self.get_session(session_id, current_user)
        if session.status == StockScanStatus.CONFIRMED:
            raise conflict("This stock session is confirmed and cannot be changed.", "STOCK_SESSION_CONFIRMED")
        if session.status == StockScanStatus.CANCELLED:
            raise bad_request("This scan session has been cancelled")
        return session

    def _session_query(self, current_user: User):
        return self.db.query(StockScanSession).options(
            selectinload(StockScanSession.items).joinedload(StockScanSessionItem.product).joinedload(Product.category),
            selectinload(StockScanSession.items).joinedload(StockScanSessionItem.product).joinedload(Product.brand),
            selectinload(StockScanSession.items).joinedload(StockScanSessionItem.product_variant),
        ).filter(StockScanSession.store_id == self._store_id(current_user))

    def _locked_variant_by_barcode(self, barcode: str, store_id: UUID) -> Optional[ProductVariant]:
        return (
            self.db.query(ProductVariant)
            .options(joinedload(ProductVariant.product))
            .filter(ProductVariant.store_id == store_id, func.lower(ProductVariant.barcode) == barcode.strip().lower())
            .with_for_update(of=ProductVariant)
            .first()
        )

    def _barcode_mapping(self, barcode: str, store_id: UUID, lock: bool = False, include_inactive: bool = False) -> Optional[ProductBarcode]:
        query = self.db.query(ProductBarcode).filter(
            ProductBarcode.store_id == store_id,
            func.lower(ProductBarcode.barcode) == barcode.strip().lower(),
        )
        if not include_inactive:
            query = query.filter(ProductBarcode.active.is_(True))
        return query.with_for_update().first() if lock else query.first()

    @staticmethod
    def _validate_barcode(barcode: str) -> None:
        if barcode.isdigit() and len(barcode) in {8, 12, 13}:
            digits = [int(value) for value in barcode]
            check_digit = digits[-1]
            payload = digits[:-1]
            total = sum(value * (3 if index % 2 == 0 else 1) for index, value in enumerate(reversed(payload)))
            if (10 - total % 10) % 10 != check_digit:
                raise bad_request("The EAN/UPC check digit is invalid. Scan it again or enter the printed barcode.", "BARCODE_CHECK_DIGIT_INVALID")

    @staticmethod
    def _barcode_type(barcode: str, requested: str) -> str:
        if requested.strip().upper() != "AUTO":
            return requested.strip().upper()
        if barcode.isdigit() and len(barcode) == 13:
            return "EAN_13"
        if barcode.isdigit() and len(barcode) == 12:
            return "UPC_A"
        if barcode.isdigit() and len(barcode) == 8:
            return "EAN_8"
        return "CODE_128"

    def _locked_inventory(self, product_id: UUID, store_id: UUID) -> ProductInventory:
        inventory = (
            self.db.query(ProductInventory)
            .filter(ProductInventory.product_id == product_id, ProductInventory.store_id == store_id)
            .with_for_update()
            .first()
        )
        if inventory:
            return inventory
        inventory = ProductInventory(product_id=product_id, store_id=store_id, current_stock=0, minimum_stock=0)
        self.db.add(inventory)
        self.db.flush()
        return inventory

    @staticmethod
    def _store_id(current_user: User) -> UUID:
        if not current_user.store_id:
            raise bad_request("Current user is not assigned to a store")
        return current_user.store_id

    @staticmethod
    def _variant_read(variant: ProductVariant, mapping: Optional[ProductBarcode] = None) -> ProductVariantBarcodeRead:
        product = variant.product
        return ProductVariantBarcodeRead(
            product_id=product.id,
            variant_id=variant.id,
            product_name=product.name,
            category=product.category.name if product.category else None,
            category_id=product.category_id,
            brand=product.brand.name if product.brand else None,
            brand_id=product.brand_id,
            size=variant.size,
            color=variant.color,
            style_code=variant.style_code,
            sku=variant.internal_sku,
            barcode=mapping.barcode if mapping else variant.barcode,
            mrp=variant.mrp,
            selling_price=variant.selling_price,
            current_physical_stock=variant.current_stock,
            current_available_stock=variant.current_stock,
            active=variant.is_active and product.is_active,
            package_quantity=mapping.package_quantity if mapping else 1,
            scan_unit=mapping.scan_unit if mapping else "PIECE",
            inventory_unit=mapping.inventory_unit if mapping else "PIECE",
            base_unit_conversion=mapping.base_unit_conversion if mapping else 1,
            sale_mode=mapping.sale_mode if mapping else "PIECE_ONLY",
        )
