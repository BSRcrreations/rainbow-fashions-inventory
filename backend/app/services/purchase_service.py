from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, text
from sqlalchemy.orm import Session, selectinload
from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

from app.ai.factory import get_ocr_service
from app.ai.invoice_parser import InvoiceParser
from app.core.exceptions import bad_request, conflict, error_payload, not_found
from app.models.brand import Brand
from app.models.category import Category
from app.models.enums import PricingType, PurchaseStatus, StockMovementType
from app.models.product import Product
from app.models.product_variant import InventoryCostLot, ProductVariant
from app.models.product_inventory import ProductInventory
from app.models.subcategory import SubCategory
from app.models.purchase import Purchase
from app.models.purchase_item import PurchaseItem
from app.models.purchase_return import PurchaseReturn, PurchaseReturnItem
from app.models.purchase_audit import PurchaseAudit
from app.models.stock_history import StockHistory
from app.models.supplier import Supplier
from app.models.user import User
from app.models.enums import DocumentJobStatus
from app.models.purchase_document import DocumentProcessingJob, PurchaseDocument
from app.repositories.product import ProductRepository
from app.repositories.purchase import PurchaseRepository
from app.schemas.purchase import (
    QuickPurchaseCreate, PurchaseReturnCreate,
    DocumentJobRead,
    ExtractedInvoice,
    PurchaseDetailRead,
    PurchaseItemPatch,
    PurchaseItemReview,
    PurchasePatch,
    PurchaseRead,
    PurchaseReviewUpdate,
    PurchaseUploadResponse,
    PurchaseValidationRead,
)
from app.services.transaction_idempotency import reserve
from app.services.file_service import FileService
from app.services.discount_calculator import (
    DiscountCalculationError,
    PurchaseInvoiceDiscountInput,
    PurchaseLineDiscountInput,
    allocate_invoice_discount,
    calculate_invoice_discount,
    calculate_purchase_line,
    money,
)


class PurchaseService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PurchaseRepository(db)
        self.product_repo = ProductRepository(db)

    def _locked_purchase(self, purchase_id, current_user):
        purchase = self.db.query(Purchase).options(selectinload(Purchase.items)).filter(Purchase.id == purchase_id, Purchase.store_id == self._store_id(current_user)).with_for_update().populate_existing().first()
        if not purchase:
            raise not_found("Purchase")
        return purchase

    def quick_purchase(self, payload: QuickPurchaseCreate, current_user: User, idempotency_key: str, purchase_id: UUID | None = None):
        try:
            record = None
            if purchase_id:
                purchase = self._locked_purchase(purchase_id, current_user)
                self._ensure_editable(purchase)
                if purchase.entry_type != "QUICK":
                    raise bad_request("Open this invoice in Purchase Review.")
                self._validate_version(purchase, payload.version)
            else:
                record, repeated = reserve(self.db, current_user, "QUICK_PURCHASE_DRAFT", idempotency_key, payload.model_dump(mode="json"))
                if repeated:
                    return self.get(UUID(record.response_snapshot["purchase_id"]), current_user)
                purchase = Purchase(store_id=self._store_id(current_user), entry_type="QUICK", purchase_date=payload.purchase_date or date.today(), status=PurchaseStatus.DRAFT, created_by=current_user.id)
                self.db.add(purchase)
                self.db.flush()
            before = self._snapshot(purchase)
            supplier = None
            if payload.supplier_id:
                supplier = self.db.query(Supplier).filter(Supplier.id == payload.supplier_id, Supplier.store_id == self._store_id(current_user), Supplier.is_active.is_(True)).first()
                if not supplier:
                    raise bad_request("Select a supplier from this store.")
            purchase.supplier_id = supplier.id if supplier else None
            purchase.supplier_name = supplier.name if supplier else payload.supplier_name or "Local Wholesale"
            purchase.invoice_number = (payload.invoice_number or "").strip() or None
            purchase.purchase_date = payload.purchase_date or date.today()
            purchase.received_date = purchase.purchase_date
            purchase.notes = payload.notes
            purchase.payment_mode = payload.payment_mode
            purchase.amount_paid = payload.amount_paid
            self._assert_unique_invoice(purchase, self._store_id(current_user))
            ids = [item.product_variant_id for item in payload.items]
            if len(ids) != len(set(ids)):
                raise bad_request("Combine quantities for the same size in one line.")
            variants = {variant.id: variant for variant in self.db.query(ProductVariant).filter(ProductVariant.id.in_(ids), ProductVariant.store_id == self._store_id(current_user), ProductVariant.is_active.is_(True)).all()}
            if len(variants) != len(ids) or any(not variant.product.is_active for variant in variants.values()):
                raise bad_request("One selected product or size is no longer available.")
            purchase.items.clear()
            self.db.flush()
            for item in payload.items:
                variant = variants[item.product_variant_id]
                purchase.items.append(self._create_purchase_item(purchase.id, PurchaseItemReview(product_id=variant.product_id, product_variant_id=variant.id, product_name=variant.product.name, size=variant.size or "", color=variant.color or "", quantity=item.quantity, purchase_price=item.purchase_cost, selling_price=item.selling_price, mrp=item.mrp, line_total=money(item.purchase_cost * item.quantity), user_verified=True, discount_verified=True)))
            self._recalculate_totals(purchase)
            if purchase.amount_paid > purchase.total_amount:
                raise bad_request("Amount paid cannot exceed the purchase total.")
            purchase.version += 1
            self._audit(purchase, "QUICK_DRAFT_SAVED", None, before, self._snapshot(purchase), current_user)
            if record:
                record.response_snapshot = {"purchase_id": str(purchase.id)}
            self.db.commit()
            return self.get(purchase.id, current_user)
        except Exception:
            self.db.rollback()
            raise

    async def attach_photo(self, purchase_id, file, current_user):
        purchase = self._locked_purchase(purchase_id, current_user)
        self._ensure_editable(purchase)
        uploaded = await FileService(self.db).save_invoice_file(file, current_user.id)
        purchase.uploaded_file_id = uploaded.id
        self._audit(purchase, "PHOTO_ATTACHED", None, {}, {"filename": uploaded.original_filename}, current_user)
        self.db.commit()
        return self.get(purchase.id, current_user)

    def list_returns(self, purchase_id, current_user):
        self.get(purchase_id, current_user)
        return self.db.query(PurchaseReturn).options(selectinload(PurchaseReturn.items)).filter(PurchaseReturn.purchase_id == purchase_id, PurchaseReturn.store_id == self._store_id(current_user)).order_by(PurchaseReturn.created_at.desc()).all()

    def create_return(self, purchase_id, payload: PurchaseReturnCreate, current_user, idempotency_key):
        try:
            record, repeated = reserve(self.db, current_user, "PURCHASE_RETURN", idempotency_key, {"purchase_id": str(purchase_id), **payload.model_dump(mode="json")})
            if repeated:
                return self.db.query(PurchaseReturn).filter_by(id=UUID(record.response_snapshot["return_id"]), store_id=self._store_id(current_user)).one()
            purchase = self._locked_purchase(purchase_id, current_user)
            if purchase.status != PurchaseStatus.CONFIRMED:
                raise bad_request("Only confirmed purchases can be returned.")
            item_map = {item.id: item for item in purchase.items}
            ids = [item.purchase_item_id for item in payload.items]
            if len(ids) != len(set(ids)) or not set(ids).issubset(item_map):
                raise bad_request("Select each received purchase item once.")
            previous = dict(self.db.query(PurchaseReturnItem.purchase_item_id, func.sum(PurchaseReturnItem.quantity)).join(PurchaseReturn).filter(PurchaseReturn.purchase_id == purchase.id, PurchaseReturn.store_id == self._store_id(current_user)).group_by(PurchaseReturnItem.purchase_item_id).all())
            result = PurchaseReturn(store_id=self._store_id(current_user), purchase_id=purchase.id, supplier_id=purchase.supplier_id, reason=payload.reason.strip(), credit_note=payload.credit_note, credit_amount=0, created_by=current_user.id)
            self.db.add(result)
            self.db.flush()
            from app.services.sale_service import SaleService
            stock = SaleService(self.db)
            for product_id in sorted({item_map[item_id].product_id for item_id in ids}, key=str):
                stock._locked_product_inventory(product_id, self._store_id(current_user))
            credit = Decimal("0")
            for requested in sorted(payload.items, key=lambda item: str(item_map[item.purchase_item_id].product_variant_id)):
                item = item_map[requested.purchase_item_id]
                if requested.quantity > int(item.accepted_quantity) - int(previous.get(item.id, 0)):
                    raise bad_request(f"Return quantity exceeds the received quantity for {item.product_name}.")
                variant = self.db.query(ProductVariant).filter_by(id=item.product_variant_id, store_id=self._store_id(current_user)).with_for_update().first()
                if not variant or variant.current_stock < requested.quantity:
                    raise bad_request(f"There is not enough stock to return {item.product_name}.")
                product, inventory = stock._locked_product_inventory(variant.product_id, self._store_id(current_user))
                before = variant.current_stock
                remaining = requested.quantity
                lots = self.db.query(InventoryCostLot).filter(InventoryCostLot.product_variant_id == variant.id, InventoryCostLot.store_id == self._store_id(current_user), InventoryCostLot.remaining_quantity > 0).order_by((InventoryCostLot.purchase_item_id == item.id).desc(), InventoryCostLot.received_date, InventoryCostLot.id).with_for_update().all()
                for lot in lots:
                    used = min(remaining, lot.remaining_quantity)
                    lot.remaining_quantity -= used
                    remaining -= used
                    if not remaining:
                        break
                if remaining:
                    raise conflict("Cost history is incomplete for this size. Reconcile inventory before returning stock.", "COST_LOT_SHORTAGE")
                variant.current_stock -= requested.quantity
                stock._sync_variant_total(product, inventory)
                amount = money(item.net_line_amount * (previous.get(item.id, 0) + requested.quantity) / item.accepted_quantity) - money(item.net_line_amount * previous.get(item.id, 0) / item.accepted_quantity)
                credit += amount
                self.db.add(PurchaseReturnItem(purchase_return_id=result.id, purchase_item_id=item.id, product_variant_id=variant.id, quantity=requested.quantity, credit_amount=amount))
                self.db.add(StockHistory(store_id=self._store_id(current_user), product_id=product.id, product_variant_id=variant.id, movement_type=StockMovementType.SUPPLIER_RETURN, qty=requested.quantity, before_stock=before, after_stock=variant.current_stock, reference=f"Purchase return {result.id}", purchase_id=purchase.id, purchase_item_id=item.id, created_by=current_user.id, unit_cost=item.landed_unit_cost))
            result.credit_amount = credit
            purchase.version += 1
            self._audit(purchase, "RETURNED", payload.reason, {}, {"return_id": str(result.id), "credit_note": payload.credit_note, "credit_amount": str(credit)}, current_user)
            record.response_snapshot = {"return_id": str(result.id)}
            self.db.commit()
            return result
        except Exception:
            self.db.rollback()
            raise

    async def upload_invoice(self, file: UploadFile, current_user: User) -> PurchaseUploadResponse:
        store_id = self._store_id(current_user)
        uploaded_file = await FileService(self.db).save_invoice_file(file, current_user.id)
        raw_text = get_ocr_service().extract_text(Path(uploaded_file.storage_path))
        extracted_invoice = InvoiceParser().parse(raw_text)
        review_items = self._build_review_items(extracted_invoice, store_id)
        supplier = self._find_supplier(extracted_invoice.supplier, store_id)

        purchase_date = extracted_invoice.date or date.today()
        image_hash = sha256(Path(uploaded_file.storage_path).read_bytes()).hexdigest()
        duplicate = self.repo.find_duplicate(store_id, extracted_invoice.supplier, extracted_invoice.invoice_number, extracted_invoice.date, extracted_invoice.total_amount)
        purchase = Purchase(
            store_id=store_id,
            supplier_id=supplier.id if supplier else None,
            uploaded_file_id=uploaded_file.id,
            invoice_number=extracted_invoice.invoice_number,
            purchase_date=purchase_date,
            invoice_date=extracted_invoice.date,
            supplier_name=extracted_invoice.supplier,
            status=PurchaseStatus.DRAFT,
            extracted_payload=jsonable_encoder(extracted_invoice),
            reviewed_payload=jsonable_encoder({"items": review_items}),
            total_amount=extracted_invoice.total_amount,
            subtotal=extracted_invoice.total_amount,
            image_hash=image_hash,
            ai_processing_status="OCR_REVIEW_REQUIRED",
            created_by=current_user.id,
        )
        self.repo.add(purchase)
        self.db.commit()
        purchase = self.repo.get_with_items(purchase.id, store_id)
        if not purchase:
            raise not_found("Purchase")
        warning = "A purchase with this invoice may already exist. Review before continuing." if duplicate else None
        return PurchaseUploadResponse(purchase=purchase, extracted_invoice=extracted_invoice, review_items=review_items, duplicate_warning=warning)

    def create_from_document(self, job_id: UUID, current_user: User) -> PurchaseUploadResponse:
        store_id = self._store_id(current_user)
        job = self.db.query(DocumentProcessingJob).filter(DocumentProcessingJob.id == job_id, DocumentProcessingJob.store_id == store_id).first()
        if not job:
            raise not_found("Document processing job")
        if job.status not in {DocumentJobStatus.REVIEW_REQUIRED, DocumentJobStatus.COMPLETED} or not job.result:
            raise bad_request("Invoice recognition is not ready for review")
        document = self.db.get(PurchaseDocument, job.document_id)
        if not document:
            raise not_found("Purchase document")
        existing = (
            self.db.query(Purchase)
            .filter(Purchase.store_id == store_id, Purchase.purchase_document_id == document.id)
            .first()
        )
        if existing:
            extracted = ExtractedInvoice.model_validate(existing.extracted_payload)
            return PurchaseUploadResponse(
                purchase=self.get(existing.id, current_user),
                extracted_invoice=extracted,
                review_items=self._review_items_from_purchase(existing),
                duplicate_warning=self._duplicate_warning(existing, store_id),
            )
        extracted_invoice = ExtractedInvoice.model_validate(job.result["extracted_invoice"])
        review_items = [PurchaseItemReview.model_validate(item) for item in job.result["review_items"]]
        supplier = self._find_supplier(extracted_invoice.supplier, store_id)
        purchase = Purchase(
            store_id=store_id,
            supplier_id=supplier.id if supplier else None,
            uploaded_file_id=document.uploaded_file_id,
            purchase_document_id=document.id,
            processing_job_id=job.id,
            invoice_number=extracted_invoice.invoice_number,
            purchase_date=extracted_invoice.date or date.today(),
            invoice_date=extracted_invoice.date,
            supplier_name=supplier.name if supplier else extracted_invoice.supplier,
            status=PurchaseStatus.DRAFT,
            extracted_payload=jsonable_encoder(extracted_invoice),
            reviewed_payload=jsonable_encoder({"items": review_items}),
            subtotal=extracted_invoice.total_amount,
            total_amount=extracted_invoice.total_amount,
            image_hash=document.sha256,
            ai_processing_status="REVIEW_REQUIRED",
            created_by=current_user.id,
        )
        self.db.add(purchase)
        self.db.flush()
        for review_item in review_items:
            purchase.items.append(self._create_purchase_item(purchase.id, review_item))
        self._recalculate_totals(purchase)
        self._audit(purchase, "CREATED_FROM_DOCUMENT", None, {}, self._snapshot(purchase), current_user)
        self.db.commit()
        purchase = self.repo.get_with_items(purchase.id, store_id)
        if not purchase:
            raise not_found("Purchase")
        warning = self._duplicate_warning(purchase, store_id)
        return PurchaseUploadResponse(purchase=purchase, extracted_invoice=extracted_invoice, review_items=review_items, duplicate_warning=warning)

    def list(self, current_user: User, skip: int = 0, limit: int = 50, status_filter: Optional[str] = None, search: Optional[str] = None) -> list[Purchase]:
        return self.repo.list_recent(self._store_id(current_user), skip, limit, status_filter, search)

    def get(self, purchase_id: UUID, current_user: User) -> Purchase:
        purchase = self.repo.get_with_items(purchase_id, self._store_id(current_user))
        if not purchase:
            raise not_found("Purchase")
        return purchase

    def detail(self, purchase_id: UUID, current_user: User) -> PurchaseDetailRead:
        purchase = self._locked_purchase(purchase_id, current_user)
        base = PurchaseRead.model_validate(purchase).model_dump()
        supplier = purchase.supplier
        document = self.db.get(PurchaseDocument, purchase.purchase_document_id) if purchase.purchase_document_id else None
        job = self.db.get(DocumentProcessingJob, purchase.processing_job_id) if purchase.processing_job_id else None
        audits = (
            self.db.query(PurchaseAudit)
            .filter(PurchaseAudit.purchase_id == purchase.id)
            .order_by(PurchaseAudit.created_at.desc())
            .all()
        )
        base.update(
            supplier=(
                {
                    "id": supplier.id,
                    "name": supplier.name,
                    "gst_number": supplier.gst_number,
                    "address": supplier.address,
                    "phone": supplier.phone,
                    "email": supplier.email,
                }
                if supplier
                else None
            ),
            document=(
                {
                    "id": document.id,
                    "original_filename": purchase.uploaded_file.original_filename,
                    "content_type": purchase.uploaded_file.content_type,
                    "file_size_bytes": purchase.uploaded_file.file_size_bytes,
                    "sha256": document.sha256,
                }
                if document and purchase.uploaded_file
                else None
            ),
            processing_job=DocumentJobRead.model_validate(job).model_dump() if job else None,
            audit_history=[
                {
                    "id": audit.id,
                    "action": audit.action,
                    "reason": audit.reason,
                    "before_data": audit.before_data,
                    "after_data": audit.after_data,
                    "performed_by": audit.performed_by_user.full_name if getattr(audit, "performed_by_user", None) else None,
                    "created_at": audit.created_at,
                }
                for audit in audits
            ],
        )
        return PurchaseDetailRead.model_validate(base)

    def invoice_file(self, purchase_id: UUID, current_user: User):
        purchase = self._locked_purchase(purchase_id, current_user)
        if not purchase.uploaded_file:
            raise not_found("Invoice document")
        return purchase.uploaded_file

    def invoice_preview(self, purchase_id: UUID, current_user: User) -> bytes:
        uploaded = self.invoice_file(purchase_id, current_user)
        if uploaded.content_type not in {"image/heic", "image/heif"}:
            raise bad_request("A converted preview is available only for HEIC or HEIF invoice images")
        try:
            register_heif_opener()
            with Image.open(uploaded.storage_path) as source:
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.thumbnail((2400, 2400))
                output = BytesIO()
                image.save(output, format="JPEG", quality=90, optimize=True)
                return output.getvalue()
        except (OSError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error_payload("The HEIC invoice image could not be prepared for preview.", "INVOICE_PREVIEW_UNAVAILABLE")) from exc

    def save_complete_draft(self, purchase_id, payload, current_user, idempotency_key):
        if not idempotency_key:
            raise bad_request("Save this draft again with a new request reference.")
        try:
            record, repeated = reserve(self.db, current_user, "PURCHASE_DRAFT_SAVE", idempotency_key,
                                       {"purchase_id": str(purchase_id), **payload.model_dump(mode="json")})
            if repeated:
                return self.get(purchase_id, current_user)
            purchase = self._locked_purchase(purchase_id, current_user)
            self._ensure_editable(purchase)
            if payload.header.version is None:
                raise bad_request("Refresh the purchase before saving changes.")
            self._validate_version(purchase, payload.header.version)
            before = self._snapshot(purchase)
            changes = payload.header.model_dump(exclude_unset=True, exclude={"version", "reason"})
            if changes.get("supplier_id"):
                supplier = self.db.query(Supplier).filter_by(id=changes["supplier_id"], store_id=self._store_id(current_user), is_active=True).first()
                if not supplier:
                    raise bad_request("Select a supplier from this store.")
                changes["supplier_name"] = supplier.name
            for field, value in changes.items():
                setattr(purchase, field, value.upper() if field == "currency" and value else value)
            # Only editable draft rows are replaced; posted evidence cannot enter this path.
            purchase.items.clear()
            self.db.flush()
            for entry in payload.items:
                if entry.product_variant_id:
                    variant = self.db.query(ProductVariant).filter_by(id=entry.product_variant_id, store_id=self._store_id(current_user), is_active=True).first()
                    if not variant:
                        raise bad_request("Select an active size from this store.")
                    if entry.product_id and entry.product_id != variant.product_id:
                        raise bad_request("The selected size does not belong to this product.")
                item = self._create_purchase_item(purchase.id, entry)
                self._synchronize_item_catalog(item, current_user)
                purchase.items.append(item)
            self._recalculate_totals(purchase)
            self._assert_unique_invoice(purchase, self._store_id(current_user))
            purchase.version += 1
            self._audit(purchase, "DRAFT_SAVED", payload.header.reason, before, self._snapshot(purchase), current_user)
            record.response_snapshot = {"purchase_id": str(purchase.id)}
            self.db.commit()
            return self.get(purchase.id, current_user)
        except Exception:
            self.db.rollback()
            raise

    def patch(self, purchase_id: UUID, payload: PurchasePatch, current_user: User) -> Purchase:
        purchase = self._locked_purchase(purchase_id, current_user)
        self._ensure_editable(purchase)
        self._validate_version(purchase, payload.version)
        before = self._snapshot(purchase)
        changes = payload.model_dump(exclude_unset=True, exclude={"version", "reason"})
        if "supplier_id" in changes and changes["supplier_id"] is not None:
            supplier = self.db.get(Supplier, changes["supplier_id"])
            if not supplier or not supplier.is_active:
                raise bad_request("Select an active supplier")
            purchase.supplier_id, purchase.supplier_name = supplier.id, supplier.name
            changes.pop("supplier_id")
            changes.pop("supplier_name", None)
        for field, value in changes.items():
            if field == "currency" and value:
                value = value.upper()
            setattr(purchase, field, value)
        self._recalculate_totals(purchase)
        self._assert_unique_invoice(purchase, self._store_id(current_user))
        purchase.version += 1
        self._audit(purchase, "UPDATED", payload.reason, before, self._snapshot(purchase), current_user)
        self.db.commit()
        return self.get(purchase.id, current_user)

    def add_item(self, purchase_id: UUID, item: PurchaseItemReview, current_user: User) -> Purchase:
        purchase = self._locked_purchase(purchase_id, current_user)
        self._ensure_editable(purchase)
        before = self._snapshot(purchase)
        purchase_item = self._create_purchase_item(purchase.id, item)
        self._synchronize_item_catalog(purchase_item, current_user)
        purchase.items.append(purchase_item)
        self._recalculate_totals(purchase)
        purchase.version += 1
        self._audit(purchase, "ITEM_ADDED", None, before, self._snapshot(purchase), current_user)
        self.db.commit()
        return self.get(purchase.id, current_user)

    def patch_item(self, purchase_id: UUID, item_id: UUID, payload: PurchaseItemPatch, current_user: User) -> Purchase:
        purchase = self._locked_purchase(purchase_id, current_user)
        self._ensure_editable(purchase)
        self._validate_version(purchase, payload.version)
        item = next((candidate for candidate in purchase.items if candidate.id == item_id), None)
        if not item:
            raise not_found("Purchase item")
        before = self._snapshot(purchase)
        for field, value in payload.model_dump(exclude_unset=True, exclude={"version", "reason"}).items():
            setattr(item, field, value)
        self._synchronize_item_catalog(item, current_user)
        if payload.discount is not None and payload.discount_type is None and payload.discount_amount is None:
            # The original API exposed one flat line discount. Preserve that
            # contract by treating it as a fixed per-line discount.
            item.discount_type = "FIXED_PER_LINE"
            item.discount_amount = payload.discount
        if payload.discount_type is not None or payload.discount_amount is not None or payload.discount_percentage is not None or payload.discount_per_unit is not None or payload.free_quantity is not None:
            item.discount_verified = True
            item.discount_verified_by = current_user.id
            item.discount_verified_at = datetime.now(timezone.utc)
        self._recalculate_totals(purchase)
        purchase.version += 1
        self._audit(purchase, "ITEM_UPDATED", payload.reason, before, self._snapshot(purchase), current_user)
        self.db.commit()
        return self.get(purchase.id, current_user)

    def delete_item(self, purchase_id: UUID, item_id: UUID, version: Optional[int], current_user: User) -> Purchase:
        purchase = self._locked_purchase(purchase_id, current_user)
        self._ensure_editable(purchase)
        self._validate_version(purchase, version)
        item = next((candidate for candidate in purchase.items if candidate.id == item_id), None)
        if not item:
            raise not_found("Purchase item")
        before = self._snapshot(purchase)
        purchase.items.remove(item)
        self._recalculate_totals(purchase)
        purchase.version += 1
        self._audit(purchase, "ITEM_DELETED", None, before, self._snapshot(purchase), current_user)
        self.db.commit()
        return self.get(purchase.id, current_user)

    def validate(self, purchase_id: UUID, current_user: User) -> PurchaseValidationRead:
        purchase = self._locked_purchase(purchase_id, current_user)
        messages: list[str] = []
        if purchase.entry_type != "QUICK" and (not purchase.invoice_number or not purchase.invoice_number.strip()):
            messages.append("Enter the supplier invoice number.")
        if not purchase.items and not purchase.reviewed_payload.get("items"):
            messages.append("Add at least one purchase item.")
        for index, item in enumerate(purchase.items, start=1):
            if item.quantity <= 0:
                messages.append(f"Quantity must be greater than zero on line {index}.")
            if not item.product_name.strip():
                messages.append(f"Select a product for line {index}.")
        if purchase.amount_paid > purchase.total_amount:
            messages.append("Amount paid cannot exceed the purchase total.")
        return PurchaseValidationRead(
            valid=not messages,
            messages=messages,
            subtotal=purchase.subtotal,
            discount=purchase.discount,
            tax_amount=purchase.tax_amount,
            total_amount=purchase.total_amount,
        )

    def cancel(self, purchase_id: UUID, reason: str, version: Optional[int], current_user: User) -> Purchase:
        purchase = self._locked_purchase(purchase_id, current_user)
        if purchase.status == PurchaseStatus.CONFIRMED:
            raise bad_request("This purchase is already confirmed. Use the correction workflow.")
        if purchase.status == PurchaseStatus.CANCELLED:
            raise bad_request("Purchase is already cancelled")
        self._validate_version(purchase, version)
        before = self._snapshot(purchase)
        purchase.status, purchase.ai_processing_status, purchase.version = PurchaseStatus.CANCELLED, "CANCELLED", purchase.version + 1
        self._audit(purchase, "CANCELLED", reason, before, self._snapshot(purchase), current_user)
        self.db.commit()
        return self.get(purchase.id, current_user)

    def update_review(self, purchase_id: UUID, payload: PurchaseReviewUpdate, current_user: User) -> Purchase:
        store_id = self._store_id(current_user)
        purchase = self._locked_purchase(purchase_id, current_user)
        self._ensure_editable(purchase)
        before = self._snapshot(purchase)
        purchase.supplier_name = payload.supplier_name
        purchase.invoice_number = payload.invoice_number
        purchase.purchase_date = payload.purchase_date
        purchase.invoice_date = payload.invoice_date
        purchase.received_date = payload.received_date
        purchase.reviewed_payload = jsonable_encoder(payload)
        self._assert_unique_invoice(purchase, store_id)
        purchase.status = PurchaseStatus.REVIEWED

        purchase.items.clear()
        self.db.flush()
        for item in payload.items:
            purchase.items.append(self._create_purchase_item(purchase.id, item))

        self._recalculate_totals(purchase)
        purchase.version += 1
        self._audit(purchase, "REVIEW_UPDATED", None, before, self._snapshot(purchase), current_user)
        self.db.commit()
        return self.get(purchase_id, current_user)

    def confirm(self, purchase_id: UUID, current_user: User) -> Purchase:
        try:
            result = self._confirm(purchase_id, current_user)
            self.db.commit()
            return result
        except Exception:
            self.db.rollback()
            raise

    def _confirm(self, purchase_id: UUID, current_user: User) -> Purchase:
        purchase = self._locked_purchase(purchase_id, current_user)
        if purchase.status == PurchaseStatus.CONFIRMED:
            return purchase
        if purchase.status in {PurchaseStatus.CANCELLED, PurchaseStatus.VOIDED}:
            raise bad_request("Cancelled purchases cannot be confirmed")
        self._assert_unique_invoice(purchase, self._store_id(current_user))

        validation = self.validate(purchase_id, current_user)
        if not validation.valid:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error_payload("Purchase discounts require review before confirmation.", "PURCHASE_VALIDATION_FAILED", [{"field": "purchase", "message": message} for message in validation.messages]))

        review_items = self._review_items_from_purchase(purchase)
        if not review_items:
            raise bad_request("Purchase has no reviewed items to confirm")

        if not purchase.items:
            for item in review_items:
                purchase.items.append(self._create_purchase_item(purchase.id, item))
            self.db.flush()

        for product_id in sorted({item.product_id or item.matched_product_id for item in purchase.items if item.product_id or item.matched_product_id}, key=str):
            self.db.query(Product).filter(Product.id == product_id, Product.store_id == self._store_id(current_user)).with_for_update().first()
        for purchase_item in sorted(purchase.items, key=lambda item: str(item.product_variant_id or item.id)):
            product = self._resolve_product_for_item(purchase_item, current_user)
            variant = self._resolve_variant_for_purchase_item(product, purchase_item, current_user)
            received_quantity = purchase_item.accepted_quantity
            if received_quantity <= 0:
                raise bad_request("Received quantity must be greater than zero.")
            if received_quantity != received_quantity.to_integral_value():
                raise bad_request("Inventory quantities must be whole units for this store.")
            stock_quantity = int(received_quantity)
            before_stock = product.current_stock
            before_variant_stock = variant.current_stock
            product.current_stock += stock_quantity
            after_stock = product.current_stock
            product.purchase_price = purchase_item.landed_unit_cost

            existing_value = variant.average_cost * before_variant_stock
            received_value = purchase_item.landed_unit_cost * stock_quantity
            variant.current_stock += stock_quantity
            variant.last_purchase_cost = purchase_item.landed_unit_cost
            variant.average_cost = (existing_value + received_value) / variant.current_stock if variant.current_stock else Decimal("0")

            inventory = self._get_or_create_inventory(product.id, current_user.store_id)
            self.db.flush()
            total = self.db.query(func.coalesce(func.sum(ProductVariant.current_stock), 0)).filter(ProductVariant.product_id == product.id, ProductVariant.store_id == current_user.store_id).scalar()
            inventory.current_stock = product.current_stock = int(total)
            if purchase_item.selling_price is not None:
                variant.selling_price = purchase_item.selling_price
            if purchase_item.mrp is not None:
                variant.mrp = purchase_item.mrp

            purchase_item.product_id = product.id
            purchase_item.product_variant_id = variant.id
            cost_lot = InventoryCostLot(
                store_id=current_user.store_id,
                product_variant_id=variant.id,
                purchase_id=purchase.id,
                purchase_item_id=purchase_item.id,
                supplier_id=purchase.supplier_id,
                received_quantity=stock_quantity,
                remaining_quantity=stock_quantity,
                unit_purchase_cost=purchase_item.purchase_price,
                allocated_landed_cost=max(Decimal("0"), purchase_item.landed_unit_cost - purchase_item.purchase_price),
                effective_unit_cost=purchase_item.landed_unit_cost,
                lot_reference=purchase.invoice_number or f"Purchase {purchase.id}",
            )
            self.db.add(cost_lot)
            self.db.flush()
            stock_history = StockHistory(
                product_id=product.id,
                product_variant_id=variant.id,
                purchase_cost_lot_id=cost_lot.id,
                store_id=current_user.store_id,
                movement_type=StockMovementType.PURCHASE,
                qty=stock_quantity,
                before_stock=before_variant_stock,
                after_stock=variant.current_stock,
                reference=purchase.invoice_number or f"Purchase {purchase.id}",
                purchase_id=purchase.id,
                purchase_item_id=purchase_item.id,
                created_by=current_user.id,
                unit_cost=purchase_item.landed_unit_cost,
            )
            self.db.add(stock_history)

        before = self._snapshot(purchase)
        purchase.status = PurchaseStatus.CONFIRMED
        purchase.confirmed_by = current_user.id
        purchase.confirmed_at = datetime.now(timezone.utc)
        purchase.ai_processing_status = "CONFIRMED"
        purchase.version += 1
        self._audit(purchase, "CONFIRMED", None, before, self._snapshot(purchase), current_user)
        self.db.flush()
        return self.get(purchase.id, current_user)

    def _build_review_items(self, extracted_invoice: ExtractedInvoice, store_id: UUID) -> list[PurchaseItemReview]:
        review_items: list[PurchaseItemReview] = []
        for item in extracted_invoice.items:
            matched, match_status = self._match_product(item.barcode, item.product_name, item.size, item.color, store_id)
            category = self._find_category(item.category, store_id)
            brand = self._find_brand(category.id, item.brand, store_id) if category else None
            review_items.append(
                PurchaseItemReview(
                    product_id=matched.id if matched else None,
                    matched_product_id=matched.id if matched else None,
                    category_id=category.id if category else None,
                    brand_id=brand.id if brand else None,
                    brand_name=item.brand,
                    category_name=item.category,
                    product_name=item.product_name,
                    barcode=item.barcode,
                    unit=item.unit,
                    size=item.size,
                    color=item.color,
                    quantity=item.quantity,
                    purchase_price=item.purchase_price,
                    list_unit_price=item.purchase_price,
                    invoiced_unit_price=item.purchase_price,
                    mrp=item.mrp,
                    line_total=item.total_amount,
                    confidence=item.confidence,
                    match_status=match_status,
                )
            )
        return review_items

    def _review_items_from_purchase(self, purchase: Purchase) -> list[PurchaseItemReview]:
        if purchase.items:
            return [
                PurchaseItemReview(
                    product_id=item.product_id,
                    matched_product_id=item.matched_product_id,
                    product_variant_id=item.product_variant_id,
                    category_id=item.category_id,
                    brand_id=item.brand_id,
                    brand_name=item.brand_name,
                    category_name=item.category_name,
                    product_name=item.product_name,
                    barcode=item.barcode,
                    supplier_product_code=item.supplier_product_code,
                    internal_sku=item.internal_sku,
                    style_code=item.style_code,
                    hsn_sac=item.hsn_sac,
                    unit=item.unit,
                    size=item.size,
                    color=item.color,
                    quantity=item.quantity,
                    purchase_price=item.purchase_price,
                    discount=item.discount,
                    list_unit_price=item.list_unit_price,
                    invoiced_unit_price=item.invoiced_unit_price,
                    discount_type=item.discount_type,
                    discount_percentage=item.discount_percentage,
                    discount_per_unit=item.discount_per_unit,
                    discount_amount=item.discount_amount,
                    discount_reason=item.discount_reason,
                    discount_source=item.discount_source,
                    free_quantity=item.free_quantity,
                    chargeable_quantity=item.chargeable_quantity,
                    accepted_quantity=item.accepted_quantity,
                    gross_amount=item.gross_amount,
                    taxable_amount=item.taxable_amount,
                    net_line_amount=item.net_line_amount,
                    effective_unit_cost=item.effective_unit_cost,
                    landed_unit_cost=item.landed_unit_cost,
                    allocated_invoice_discount=item.allocated_invoice_discount,
                    promotion_id=item.promotion_id,
                    discount_rule_id=item.discount_rule_id,
                    discount_verified=item.discount_verified,
                    tax_amount=item.tax_amount,
                    tax_rate=item.tax_rate,
                    mrp=item.mrp,
                    selling_price=item.selling_price,
                    line_total=item.line_total,
                    confidence=item.confidence,
                    match_status=item.match_status,
                    batch_number=item.batch_number,
                    expiry_date=item.expiry_date,
                    user_verified=item.user_verified,
                )
                for item in purchase.items
            ]
        return [PurchaseItemReview.model_validate(item) for item in purchase.reviewed_payload.get("items", [])]

    def _create_purchase_item(self, purchase_id: UUID, item: PurchaseItemReview) -> PurchaseItem:
        discount_type = item.discount_type
        if discount_type == "NONE" and item.discount > 0 and item.discount_amount is None:
            discount_type = "FIXED_PER_LINE"
        return PurchaseItem(
            purchase_id=purchase_id,
            product_id=item.product_id,
            matched_product_id=item.matched_product_id,
            product_variant_id=item.product_variant_id,
            category_id=item.category_id,
            brand_id=item.brand_id,
            brand_name=item.brand_name,
            category_name=item.category_name,
            product_name=item.product_name.strip(),
            barcode=item.barcode.strip() if item.barcode else None,
            supplier_product_code=item.supplier_product_code.strip() if item.supplier_product_code else None,
            internal_sku=item.internal_sku.strip() if item.internal_sku else None,
            style_code=item.style_code.strip() if item.style_code else None,
            hsn_sac=item.hsn_sac.strip() if item.hsn_sac else None,
            unit=item.unit.strip(),
            size=item.size.strip(),
            color=item.color.strip(),
            quantity=item.quantity,
            purchase_price=item.purchase_price,
            discount=item.discount,
            list_unit_price=item.list_unit_price if item.list_unit_price is not None else item.purchase_price,
            invoiced_unit_price=item.invoiced_unit_price,
            discount_type=discount_type,
            discount_percentage=item.discount_percentage,
            discount_per_unit=item.discount_per_unit,
            discount_amount=item.discount_amount if item.discount_amount is not None else item.discount,
            discount_reason=item.discount_reason,
            discount_source=item.discount_source,
            free_quantity=item.free_quantity,
            chargeable_quantity=item.chargeable_quantity if item.chargeable_quantity is not None else Decimal(item.quantity),
            accepted_quantity=item.accepted_quantity if item.accepted_quantity is not None else Decimal(item.quantity) + item.free_quantity,
            gross_amount=item.gross_amount if item.gross_amount is not None else Decimal(item.quantity) * item.purchase_price,
            taxable_amount=item.taxable_amount if item.taxable_amount is not None else item.line_total - item.tax_amount,
            net_line_amount=item.net_line_amount if item.net_line_amount is not None else item.line_total,
            effective_unit_cost=item.effective_unit_cost if item.effective_unit_cost is not None else item.purchase_price,
            landed_unit_cost=item.landed_unit_cost if item.landed_unit_cost is not None else item.purchase_price,
            allocated_invoice_discount=item.allocated_invoice_discount,
            promotion_id=item.promotion_id,
            discount_rule_id=item.discount_rule_id,
            discount_verified=item.discount_verified,
            tax_amount=item.tax_amount,
            tax_rate=item.tax_rate,
            mrp=item.mrp,
            selling_price=item.selling_price,
            line_total=item.line_total,
            confidence=item.confidence,
            match_status=item.match_status,
            batch_number=item.batch_number.strip() if item.batch_number else None,
            expiry_date=item.expiry_date,
            user_verified=item.user_verified,
        )

    def _resolve_product_for_item(self, item: PurchaseItem, current_user: User) -> Product:
        store_id = self._store_id(current_user)
        identified_variant = self._variant_from_exact_item_identifiers(item, store_id)
        if identified_variant:
            product_id = item.product_id or item.matched_product_id
            if product_id and product_id != identified_variant.product_id:
                raise bad_request("The purchase barcode or internal SKU belongs to a different product.")
            product = self.db.get(Product, identified_variant.product_id)
            if not product or product.store_id != store_id:
                raise bad_request("The identified purchase product is not available in this store.")
            return product

        product_id = item.product_id or item.matched_product_id
        if product_id:
            product = self.db.get(Product, product_id)
            if product and product.store_id == store_id:
                return product
            raise bad_request("The selected product is not available in this store.")

        category = self.db.query(Category).filter(Category.id == item.category_id, Category.store_id == store_id).first() if item.category_id else self._get_or_create_category(item.category_name, store_id)
        brand = self.db.query(Brand).filter(Brand.id == item.brand_id, Brand.store_id == store_id).first() if item.brand_id else self._get_or_create_brand(category.id if category else None, item.brand_name, store_id)
        if not category or not brand:
            raise bad_request(f"Category and brand are required for new product: {item.product_name}")
        if brand.category_id != category.id:
            raise bad_request(f"Brand does not belong to category for new product: {item.product_name}")
        subcategory = self._get_or_create_default_subcategory(category.id, store_id)

        duplicate = self.product_repo.get_duplicate(category.id, subcategory.id, brand.id, item.product_name)
        if duplicate:
            return duplicate

        product = Product(
            store_id=current_user.store_id,
            category_id=category.id,
            subcategory_id=subcategory.id,
            brand_id=brand.id,
            name=item.product_name,
            size=item.size,
            color=item.color,
            purchase_price=item.purchase_price,
            selling_price=item.selling_price or item.mrp or item.purchase_price,
            pricing_type=PricingType.MRP if item.mrp else PricingType.OWN_PRICE,
            mrp=item.mrp,
            current_stock=0,
            minimum_stock=0,
            barcode=None,
        )
        self.db.add(product)
        self.db.flush()
        self.db.refresh(product)
        return product

    def _resolve_variant_for_purchase_item(self, product: Product, item: PurchaseItem, current_user: User) -> ProductVariant:
        """Return the precise sellable variant for a reviewed purchase line."""
        store_id = self._store_id(current_user)
        identified_variant = self._variant_from_exact_item_identifiers(item, store_id)
        if identified_variant:
            if identified_variant.product_id != product.id:
                raise bad_request("The purchase barcode or internal SKU belongs to a different product.")
            return identified_variant

        if item.product_variant_id:
            variant = (
                self.db.query(ProductVariant)
                .filter(
                    ProductVariant.id == item.product_variant_id,
                    ProductVariant.product_id == product.id,
                    ProductVariant.store_id == store_id,
                )
                .with_for_update()
                .first()
            )
            if not variant:
                raise bad_request("Selected product variant does not belong to this product or store")
            return variant

        candidates = self.db.query(ProductVariant).filter(ProductVariant.product_id == product.id, ProductVariant.store_id == store_id, ProductVariant.is_active.is_(True)).with_for_update().all()
        if candidates and not item.create_new_product:
            matches = [variant for variant in candidates if (variant.size or "").strip().casefold() == (item.size or "").strip().casefold() and (variant.color or "").strip().casefold() == (item.color or "").strip().casefold()]
            if len(matches) == 1:
                return matches[0]
            raise bad_request(f"Choose the exact size for {product.name} before confirming the purchase.")

        def normalized(value: Optional[str]) -> str:
            return (value or "").strip().casefold()

        selling_price = item.selling_price or item.mrp or product.selling_price
        mrp = item.mrp or product.mrp
        base_identity = "|".join(
            [
                normalized(item.size),
                normalized(item.color),
                normalized(item.style_code),
                normalized(item.supplier_product_code),
                normalized(item.internal_sku),
                normalized(item.barcode),
                str(mrp or ""),
                str(selling_price),
            ]
        )
        identity_key = f"{product.id}|{base_identity}"
        variant = (
            self.db.query(ProductVariant)
            .filter(ProductVariant.store_id == store_id, ProductVariant.product_id == product.id, ProductVariant.identity_key == identity_key)
            .first()
        )
        if variant:
            return variant

        same_attribute_variants = (
            self.db.query(ProductVariant)
            .filter(
                ProductVariant.store_id == store_id,
                ProductVariant.product_id == product.id,
                func.coalesce(ProductVariant.size, "") == (item.size or ""),
                func.coalesce(ProductVariant.color, "") == (item.color or ""),
            )
            .count()
        )
        style_code = item.style_code or (f"TEMP-{same_attribute_variants + 1}" if same_attribute_variants else None)
        internal_sku = item.internal_sku or item.supplier_product_code or f"RFV-{str(product.id)[:8]}-{uuid4().hex[:8].upper()}"
        barcode = item.barcode or f"RFV-{uuid4().hex[:16].upper()}"
        if self.db.query(ProductVariant.id).filter(ProductVariant.store_id == store_id, ProductVariant.internal_sku == internal_sku).first():
            internal_sku = f"{internal_sku}-{uuid4().hex[:6].upper()}"
        if self.db.query(ProductVariant.id).filter(ProductVariant.store_id == store_id, ProductVariant.barcode == barcode).first():
            barcode = f"RFV-{uuid4().hex[:16].upper()}"
        variant = ProductVariant(
            store_id=store_id,
            product_id=product.id,
            size=item.size or None,
            color=item.color or None,
            style_code=style_code,
            manufacturer_sku=item.supplier_product_code or None,
            internal_sku=internal_sku,
            barcode=barcode,
            identity_key=identity_key,
            mrp=mrp,
            selling_price=selling_price,
            last_purchase_cost=item.landed_unit_cost,
            average_cost=item.landed_unit_cost,
            current_stock=0,
            classification_review_required=not bool(item.style_code or item.internal_sku or item.supplier_product_code or item.barcode),
        )
        item.internal_sku = internal_sku
        item.style_code = style_code
        item.selling_price = selling_price
        self.db.add(variant)
        self.db.flush()
        return variant

    def _variant_from_exact_item_identifiers(self, item: PurchaseItem, store_id: UUID) -> Optional[ProductVariant]:
        """Resolve reviewed invoice identifiers before any new catalogue record is created."""
        matches: list[ProductVariant] = []
        for field, raw_value in ((ProductVariant.barcode, item.barcode), (ProductVariant.internal_sku, item.internal_sku)):
            value = (raw_value or "").strip()
            if not value:
                continue
            match = (
                self.db.query(ProductVariant)
                .filter(
                    ProductVariant.store_id == store_id,
                    ProductVariant.is_active.is_(True),
                    func.lower(field) == value.casefold(),
                )
                .with_for_update()
                .first()
            )
            if match:
                matches.append(match)
        if not matches:
            return None
        if any(match.id != matches[0].id for match in matches[1:]):
            raise bad_request("The purchase barcode and internal SKU identify different variants.")
        return matches[0]

    def _synchronize_item_catalog(self, item: PurchaseItem, current_user: User) -> None:
        store_id = self._store_id(current_user)
        category = self.db.query(Category).filter(Category.id == item.category_id, Category.store_id == store_id).first() if item.category_id else None
        brand = self.db.query(Brand).filter(Brand.id == item.brand_id, Brand.store_id == store_id).first() if item.brand_id else None
        if item.category_id and not category:
            raise bad_request("Selected category was not found")
        if item.brand_id and not brand:
            raise bad_request("Selected brand was not found")
        if brand and category and brand.category_id != category.id:
            raise bad_request("Selected brand does not belong to the selected category")
        if brand and not category:
            category = self.db.query(Category).filter(Category.id == brand.category_id, Category.store_id == store_id).first()
            if not category:
                raise bad_request("Category for the selected brand was not found")
            item.category_id = category.id
        if category:
            item.category_name = category.name
        if brand:
            item.brand_name = brand.name

    def _get_or_create_inventory(self, product_id: UUID, store_id: Optional[UUID]) -> ProductInventory:
        if store_id is None:
            raise bad_request("Current user is not assigned to a store")
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

    def _match_product(self, barcode: Optional[str], name: str, size: str, color: str, store_id: UUID) -> tuple[Optional[Product], str]:
        if barcode:
            product = self.db.query(Product).filter(Product.store_id == store_id, Product.barcode == barcode.strip()).first()
            if product:
                return product, "EXACT_BARCODE"
        product = self.db.query(Product).filter(Product.store_id == store_id, Product.sku == name.strip()).first()
        if product:
            return product, "EXACT_SKU"
        product = self.db.query(Product).filter(func.lower(Product.name) == name.strip().lower(), func.lower(Product.size) == size.strip().lower(), func.lower(Product.color) == color.strip().lower()).first()
        return (product, "EXACT_NAME" if product else "NOT_FOUND")

    def _store_id(self, current_user: User) -> UUID:
        if current_user.store_id is None:
            raise bad_request("Current user is not assigned to a store")
        return current_user.store_id

    def _find_category(self, name: Optional[str], store_id: UUID) -> Optional[Category]:
        if not name:
            return None
        return self.db.query(Category).filter(Category.store_id == store_id, func.lower(Category.name) == name.strip().lower()).first()

    def _find_brand(self, category_id: UUID, name: Optional[str], store_id: UUID) -> Optional[Brand]:
        if not category_id or not name:
            return None
        return self.db.query(Brand).filter(Brand.store_id == store_id, Brand.category_id == category_id, func.lower(Brand.name) == name.strip().lower()).first()

    def _get_or_create_category(self, name: Optional[str], store_id: UUID) -> Optional[Category]:
        if not name:
            return None
        category = self._find_category(name, store_id)
        if category:
            return category
        category = Category(store_id=store_id, name=name.strip(), description="Created from invoice extraction")
        self.db.add(category)
        self.db.flush()
        return category

    def _get_or_create_brand(self, category_id: Optional[UUID], name: Optional[str], store_id: UUID) -> Optional[Brand]:
        if not category_id or not name:
            return None
        brand = self._find_brand(category_id, name, store_id)
        if brand:
            return brand
        brand = Brand(store_id=store_id, category_id=category_id, name=name.strip(), description="Created from invoice extraction")
        self.db.add(brand)
        self.db.flush()
        return brand

    def _get_or_create_default_subcategory(self, category_id: UUID, store_id: UUID) -> SubCategory:
        subcategory = (
            self.db.query(SubCategory)
            .filter(SubCategory.store_id == store_id, SubCategory.category_id == category_id, func.lower(SubCategory.name) == "general")
            .first()
        )
        if subcategory:
            return subcategory
        subcategory = SubCategory(store_id=store_id, category_id=category_id, name="General", description="Default product group")
        self.db.add(subcategory)
        self.db.flush()
        return subcategory

    def _find_supplier(self, name: Optional[str], store_id: UUID) -> Optional[Supplier]:
        if not name:
            return None
        return self.db.query(Supplier).filter(Supplier.store_id == store_id, func.lower(Supplier.name) == name.strip().casefold(), Supplier.is_active.is_(True)).first()

    def _ensure_editable(self, purchase: Purchase) -> None:
        if purchase.status == PurchaseStatus.CONFIRMED:
            raise bad_request("This purchase is already confirmed. Use the correction workflow.")
        if purchase.status == PurchaseStatus.CANCELLED:
            raise bad_request("Cancelled purchases cannot be edited")

    @staticmethod
    def _validate_version(purchase: Purchase, version: Optional[int]) -> None:
        if version is not None and purchase.version != version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_payload("This purchase was changed by another user. Reload and review the latest version.", "PURCHASE_MODIFIED"),
            )

    def _assert_unique_invoice(self, purchase: Purchase, store_id: UUID) -> None:
        if purchase.invoice_number:
            identity = f"{store_id}:{purchase.supplier_id or (purchase.supplier_name or '').strip().casefold()}:{purchase.invoice_number.strip().casefold()}"
            lock_id = int.from_bytes(sha256(identity.encode()).digest()[:8], "big", signed=True)
            self.db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id})
        duplicate = self.repo.find_duplicate_invoice(store_id, purchase.supplier_id, purchase.supplier_name, purchase.invoice_number, purchase.id)
        if duplicate:
            raise conflict("This invoice number already exists for this supplier.")

    def _duplicate_warning(self, purchase: Purchase, store_id: UUID) -> Optional[str]:
        duplicate = self.repo.find_duplicate_invoice(store_id, purchase.supplier_id, purchase.supplier_name, purchase.invoice_number, purchase.id)
        return "This invoice number already exists for this supplier." if duplicate else None

    def _recalculate_totals(self, purchase: Purchase) -> None:
        try:
            rows = [
                calculate_purchase_line(
                    PurchaseLineDiscountInput(
                        chargeable_quantity=item.chargeable_quantity if item.chargeable_quantity is not None else Decimal(item.quantity),
                        free_quantity=item.free_quantity or Decimal("0"),
                        list_unit_price=item.list_unit_price if item.list_unit_price is not None else item.purchase_price,
                        discount_type=item.discount_type,
                        discount_percentage=item.discount_percentage or Decimal("0"),
                        discount_per_unit=item.discount_per_unit or Decimal("0"),
                        discount_amount=item.discount_amount if item.discount_amount is not None else item.discount,
                        invoiced_unit_price=item.invoiced_unit_price,
                        tax_rate=purchase.invoice_tax_rate or Decimal("0"),
                        manual_reason=item.discount_reason,
                    )
                )
                for item in purchase.items
            ]
            if any(row.chargeable_quantity != row.chargeable_quantity.to_integral_value() for row in rows):
                raise DiscountCalculationError("Chargeable quantity must be a whole unit for this store.")
            if any(row.received_quantity != row.received_quantity.to_integral_value() for row in rows):
                raise DiscountCalculationError("Received quantity must be a whole unit for this store.")
            invoice_discount = calculate_invoice_discount(
                PurchaseInvoiceDiscountInput(
                    discount_type=purchase.invoice_discount_type,
                    discount_percentage=purchase.invoice_discount_percentage or Decimal("0"),
                    discount_amount=purchase.invoice_discount_amount or Decimal("0"),
                    allocation_method=purchase.invoice_discount_allocation_method,
                    manual_reason=purchase.invoice_discount_reason,
                ),
                sum((row.taxable_amount for row in rows), Decimal("0")),
            )
            allocations = allocate_invoice_discount(invoice_discount, rows, purchase.invoice_discount_allocation_method)
        except DiscountCalculationError as exc:
            raise bad_request(str(exc), "DISCOUNT_VALIDATION_FAILED") from exc

        landed_charge_total = money((purchase.packaging_amount or Decimal("0")) + (purchase.freight_amount or Decimal("0")))
        received_total = sum((row.received_quantity for row in rows), Decimal("0"))
        for item, row, allocation in zip(purchase.items, rows, allocations):
            taxable_amount = money(row.taxable_amount - allocation)
            item.tax_rate = purchase.invoice_tax_rate or Decimal("0")
            tax_amount = money(taxable_amount * item.tax_rate / Decimal("100"))
            landed_charge = money(landed_charge_total * row.received_quantity / received_total) if received_total else Decimal("0.00")
            item.quantity = int(row.chargeable_quantity)
            item.chargeable_quantity = row.chargeable_quantity
            item.free_quantity = row.free_quantity
            item.accepted_quantity = row.received_quantity
            item.list_unit_price = item.list_unit_price if item.list_unit_price is not None else item.purchase_price
            item.purchase_price = item.list_unit_price
            item.gross_amount = row.gross_amount
            item.discount_amount = row.item_discount_amount
            item.discount = row.item_discount_amount
            item.allocated_invoice_discount = allocation
            item.taxable_amount = taxable_amount
            item.tax_amount = tax_amount
            item.net_line_amount = money(taxable_amount + tax_amount)
            item.line_total = item.net_line_amount
            item.effective_unit_cost = money(taxable_amount / row.received_quantity) if row.received_quantity else Decimal("0.00")
            item.landed_unit_cost = money((taxable_amount + landed_charge) / row.received_quantity) if row.received_quantity else Decimal("0.00")
        purchase.subtotal = sum((row.gross_amount for row in rows), Decimal("0"))
        purchase.invoice_discount_amount = invoice_discount
        purchase.discount = money(sum((row.item_discount_amount for row in rows), Decimal("0")) + invoice_discount)
        purchase.tax_amount = sum((item.tax_amount for item in purchase.items), Decimal("0"))
        unallocated_invoice_discount = (
            invoice_discount if purchase.invoice_discount_allocation_method == "DO_NOT_ALLOCATE" else Decimal("0.00")
        )
        purchase.total_amount = money(
            sum((item.net_line_amount for item in purchase.items), Decimal("0"))
            - unallocated_invoice_discount
            + landed_charge_total
            + (purchase.round_off or Decimal("0"))
        )
        purchase.reviewed_payload = jsonable_encoder({"items": self._review_items_from_purchase(purchase)})

    @staticmethod
    def _snapshot(purchase: Purchase) -> dict:
        return {
            "invoice_number": purchase.invoice_number,
            "supplier_id": str(purchase.supplier_id) if purchase.supplier_id else None,
            "supplier_name": purchase.supplier_name,
            "purchase_date": purchase.purchase_date,
            "invoice_date": purchase.invoice_date,
            "received_date": purchase.received_date,
            "due_date": purchase.due_date,
            "payment_mode": purchase.payment_mode,
            "amount_paid": purchase.amount_paid,
            "subtotal": purchase.subtotal,
            "discount": purchase.discount,
            "invoice_discount_type": purchase.invoice_discount_type,
            "invoice_discount_amount": purchase.invoice_discount_amount,
            "tax_amount": purchase.tax_amount,
            "total_amount": purchase.total_amount,
            "status": purchase.status.value,
            "version": purchase.version,
            "items": [
                {
                    "id": str(item.id) if item.id else None,
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "purchase_price": item.purchase_price,
                    "list_unit_price": item.list_unit_price,
                    "discount_type": item.discount_type,
                    "discount_amount": item.discount_amount,
                    "free_quantity": item.free_quantity,
                    "taxable_amount": item.taxable_amount,
                    "effective_unit_cost": item.effective_unit_cost,
                    "tax_amount": item.tax_amount,
                    "line_total": item.line_total,
                }
                for item in purchase.items
            ],
        }

    def _audit(self, purchase: Purchase, action: str, reason: Optional[str], before: dict, after: dict, current_user: User) -> None:
        self.db.add(
            PurchaseAudit(
                purchase=purchase,
                action=action,
                reason=reason,
                before_data=jsonable_encoder(before),
                after_data=jsonable_encoder(after),
                performed_by=current_user.id,
            )
        )
