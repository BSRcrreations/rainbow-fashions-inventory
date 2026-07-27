from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai.factory import get_ocr_service
from app.ai.invoice_parser import InvoiceParser
from app.core.exceptions import bad_request, conflict, error_payload, not_found
from app.models.brand import Brand
from app.models.category import Category
from app.models.enums import PricingType, PurchaseStatus, StockMovementType
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.product_inventory import ProductInventory
from app.models.subcategory import SubCategory
from app.models.purchase import Purchase
from app.models.purchase_item import PurchaseItem
from app.models.purchase_audit import PurchaseAudit
from app.models.stock_history import StockHistory
from app.models.supplier import Supplier
from app.models.user import User
from app.models.enums import DocumentJobStatus
from app.models.purchase_document import DocumentProcessingJob, PurchaseDocument
from app.repositories.product import ProductRepository
from app.repositories.purchase import PurchaseRepository
from app.schemas.purchase import (
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
from app.services.file_service import FileService


class PurchaseService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PurchaseRepository(db)
        self.product_repo = ProductRepository(db)

    async def upload_invoice(self, file: UploadFile, current_user: User) -> PurchaseUploadResponse:
        store_id = self._store_id(current_user)
        uploaded_file = await FileService(self.db).save_invoice_file(file, current_user.id)
        raw_text = get_ocr_service().extract_text(Path(uploaded_file.storage_path))
        extracted_invoice = InvoiceParser().parse(raw_text)
        review_items = self._build_review_items(extracted_invoice)
        supplier = self._find_supplier(extracted_invoice.supplier)

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
        supplier = self._find_supplier(extracted_invoice.supplier)
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
        self._audit(purchase, "CREATED_FROM_DOCUMENT", None, {}, self._snapshot(purchase), current_user)
        self.db.commit()
        purchase = self.repo.get_with_items(purchase.id, store_id)
        if not purchase:
            raise not_found("Purchase")
        warning = self._duplicate_warning(purchase, store_id)
        return PurchaseUploadResponse(purchase=purchase, extracted_invoice=extracted_invoice, review_items=review_items, duplicate_warning=warning)

    def list(self, current_user: User, skip: int = 0, limit: int = 50) -> list[Purchase]:
        return self.repo.list_recent(self._store_id(current_user), skip, limit)

    def get(self, purchase_id: UUID, current_user: User) -> Purchase:
        purchase = self.repo.get_with_items(purchase_id, self._store_id(current_user))
        if not purchase:
            raise not_found("Purchase")
        return purchase

    def detail(self, purchase_id: UUID, current_user: User) -> PurchaseDetailRead:
        purchase = self.get(purchase_id, current_user)
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
        purchase = self.get(purchase_id, current_user)
        if not purchase.uploaded_file:
            raise not_found("Invoice document")
        return purchase.uploaded_file

    def patch(self, purchase_id: UUID, payload: PurchasePatch, current_user: User) -> Purchase:
        purchase = self.get(purchase_id, current_user)
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
        self._assert_unique_invoice(purchase, self._store_id(current_user))
        purchase.version += 1
        self._audit(purchase, "UPDATED", payload.reason, before, self._snapshot(purchase), current_user)
        self.db.commit()
        return self.get(purchase.id, current_user)

    def add_item(self, purchase_id: UUID, item: PurchaseItemReview, current_user: User) -> Purchase:
        purchase = self.get(purchase_id, current_user)
        self._ensure_editable(purchase)
        before = self._snapshot(purchase)
        purchase.items.append(self._create_purchase_item(purchase.id, item))
        self._recalculate_totals(purchase)
        purchase.version += 1
        self._audit(purchase, "ITEM_ADDED", None, before, self._snapshot(purchase), current_user)
        self.db.commit()
        return self.get(purchase.id, current_user)

    def patch_item(self, purchase_id: UUID, item_id: UUID, payload: PurchaseItemPatch, current_user: User) -> Purchase:
        purchase = self.get(purchase_id, current_user)
        self._ensure_editable(purchase)
        self._validate_version(purchase, payload.version)
        item = next((candidate for candidate in purchase.items if candidate.id == item_id), None)
        if not item:
            raise not_found("Purchase item")
        before = self._snapshot(purchase)
        for field, value in payload.model_dump(exclude_unset=True, exclude={"version", "reason"}).items():
            setattr(item, field, value)
        self._recalculate_totals(purchase)
        purchase.version += 1
        self._audit(purchase, "ITEM_UPDATED", payload.reason, before, self._snapshot(purchase), current_user)
        self.db.commit()
        return self.get(purchase.id, current_user)

    def delete_item(self, purchase_id: UUID, item_id: UUID, version: Optional[int], current_user: User) -> Purchase:
        purchase = self.get(purchase_id, current_user)
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
        purchase = self.get(purchase_id, current_user)
        messages: list[str] = []
        if not purchase.invoice_number or not purchase.invoice_number.strip():
            messages.append("Enter the supplier invoice number.")
        if not purchase.items and not purchase.reviewed_payload.get("items"):
            messages.append("Add at least one purchase item.")
        for index, item in enumerate(purchase.items, start=1):
            if item.quantity <= 0:
                messages.append(f"Quantity must be greater than zero on line {index}.")
            if not item.product_name.strip():
                messages.append(f"Select a product for line {index}.")
        return PurchaseValidationRead(
            valid=not messages,
            messages=messages,
            subtotal=purchase.subtotal,
            discount=purchase.discount,
            tax_amount=purchase.tax_amount,
            total_amount=purchase.total_amount,
        )

    def cancel(self, purchase_id: UUID, reason: str, version: Optional[int], current_user: User) -> Purchase:
        purchase = self.get(purchase_id, current_user)
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
        purchase = self.get(purchase_id, current_user)
        self._ensure_editable(purchase)
        before = self._snapshot(purchase)
        purchase.supplier_name = payload.supplier_name
        purchase.invoice_number = payload.invoice_number
        purchase.purchase_date = payload.purchase_date
        purchase.invoice_date = payload.invoice_date
        purchase.received_date = payload.received_date
        purchase.reviewed_payload = jsonable_encoder(payload)
        purchase.subtotal = sum((item.quantity * item.purchase_price for item in payload.items), Decimal("0"))
        purchase.discount = sum((item.discount for item in payload.items), Decimal("0"))
        purchase.tax_amount = sum((item.tax_amount for item in payload.items), Decimal("0"))
        purchase.total_amount = sum((item.line_total for item in payload.items), Decimal("0"))
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
        purchase = self.get(purchase_id, current_user)
        if purchase.status == PurchaseStatus.CONFIRMED:
            raise bad_request("Purchase is already confirmed")
        if purchase.status == PurchaseStatus.CANCELLED:
            raise bad_request("Cancelled purchases cannot be confirmed")

        review_items = self._review_items_from_purchase(purchase)
        if not review_items:
            raise bad_request("Purchase has no reviewed items to confirm")

        if not purchase.items:
            for item in review_items:
                purchase.items.append(self._create_purchase_item(purchase.id, item))
            self.db.flush()

        for purchase_item in purchase.items:
            product = self._resolve_product_for_item(purchase_item)
            before_stock = product.current_stock
            product.current_stock += purchase_item.quantity
            after_stock = product.current_stock

            inventory = self._get_or_create_inventory(product.id, current_user.store_id)
            inventory.current_stock += purchase_item.quantity

            purchase_item.product_id = product.id
            stock_history = StockHistory(
                product_id=product.id,
                store_id=current_user.store_id,
                movement_type=StockMovementType.PURCHASE,
                qty=purchase_item.quantity,
                before_stock=before_stock,
                after_stock=after_stock,
                reference=purchase.invoice_number or f"Purchase {purchase.id}",
                purchase_id=purchase.id,
                purchase_item_id=purchase_item.id,
                created_by=current_user.id,
            )
            self.db.add(stock_history)

        before = self._snapshot(purchase)
        purchase.status = PurchaseStatus.CONFIRMED
        purchase.confirmed_by = current_user.id
        purchase.confirmed_at = datetime.now(timezone.utc)
        purchase.ai_processing_status = "CONFIRMED"
        purchase.version += 1
        self._audit(purchase, "CONFIRMED", None, before, self._snapshot(purchase), current_user)
        self.db.commit()
        return self.get(purchase.id, current_user)

    def _build_review_items(self, extracted_invoice: ExtractedInvoice) -> list[PurchaseItemReview]:
        review_items: list[PurchaseItemReview] = []
        for item in extracted_invoice.items:
            matched, match_status = self._match_product(item.barcode, item.product_name, item.size, item.color)
            category = self._find_category(item.category)
            brand = self._find_brand(category.id, item.brand) if category else None
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
                    category_id=item.category_id,
                    brand_id=item.brand_id,
                    brand_name=item.brand_name,
                    category_name=item.category_name,
                    product_name=item.product_name,
                    barcode=item.barcode,
                supplier_product_code=item.supplier_product_code,
                hsn_sac=item.hsn_sac,
                unit=item.unit,
                    size=item.size,
                    color=item.color,
                    quantity=item.quantity,
                    purchase_price=item.purchase_price,
                    discount=item.discount,
                tax_amount=item.tax_amount,
                tax_rate=item.tax_rate,
                    mrp=item.mrp,
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
        return PurchaseItem(
            purchase_id=purchase_id,
            product_id=item.product_id,
            matched_product_id=item.matched_product_id,
            category_id=item.category_id,
            brand_id=item.brand_id,
            brand_name=item.brand_name,
            category_name=item.category_name,
            product_name=item.product_name.strip(),
            barcode=item.barcode.strip() if item.barcode else None,
            supplier_product_code=item.supplier_product_code.strip() if item.supplier_product_code else None,
            hsn_sac=item.hsn_sac.strip() if item.hsn_sac else None,
            unit=item.unit.strip(),
            size=item.size.strip(),
            color=item.color.strip(),
            quantity=item.quantity,
            purchase_price=item.purchase_price,
            discount=item.discount,
            tax_amount=item.tax_amount,
            tax_rate=item.tax_rate,
            mrp=item.mrp,
            line_total=item.line_total,
            confidence=item.confidence,
            match_status=item.match_status,
            batch_number=item.batch_number.strip() if item.batch_number else None,
            expiry_date=item.expiry_date,
            user_verified=item.user_verified,
        )

    def _resolve_product_for_item(self, item: PurchaseItem) -> Product:
        product_id = item.product_id or item.matched_product_id
        if product_id:
            product = self.db.get(Product, product_id)
            if product:
                return product

        category = self.db.get(Category, item.category_id) if item.category_id else self._get_or_create_category(item.category_name)
        brand = self.db.get(Brand, item.brand_id) if item.brand_id else self._get_or_create_brand(category.id if category else None, item.brand_name)
        if not category or not brand:
            raise bad_request(f"Category and brand are required for new product: {item.product_name}")
        if brand.category_id != category.id:
            raise bad_request(f"Brand does not belong to category for new product: {item.product_name}")
        subcategory = self._get_or_create_default_subcategory(category.id)

        duplicate = self.product_repo.get_duplicate(category.id, subcategory.id, brand.id, item.product_name)
        if duplicate:
            has_variant = any(
                (variant.size or "").casefold() == (item.size or "").casefold()
                and (variant.color or "").casefold() == (item.color or "").casefold()
                for variant in duplicate.variants
            )
            if not has_variant and (item.size or item.color):
                duplicate.variants.append(ProductVariant(size=item.size or None, color=item.color or None))
            return duplicate

        product = Product(
            category_id=category.id,
            subcategory_id=subcategory.id,
            brand_id=brand.id,
            name=item.product_name,
            size=item.size,
            color=item.color,
            purchase_price=item.purchase_price,
            selling_price=item.mrp or item.purchase_price,
            pricing_type=PricingType.MRP if item.mrp else PricingType.OWN_PRICE,
            mrp=item.mrp,
            current_stock=0,
            minimum_stock=0,
            barcode=None,
        )
        if item.size or item.color:
            product.variants.append(ProductVariant(size=item.size or None, color=item.color or None))
        self.db.add(product)
        self.db.flush()
        self.db.refresh(product)
        return product

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

    def _match_product(self, barcode: Optional[str], name: str, size: str, color: str) -> tuple[Optional[Product], str]:
        if barcode:
            product = self.db.query(Product).filter(Product.barcode == barcode.strip()).first()
            if product:
                return product, "EXACT_BARCODE"
        product = self.db.query(Product).filter(Product.sku == name.strip()).first()
        if product:
            return product, "EXACT_SKU"
        product = self.db.query(Product).filter(func.lower(Product.name) == name.strip().lower(), func.lower(Product.size) == size.strip().lower(), func.lower(Product.color) == color.strip().lower()).first()
        return (product, "EXACT_NAME" if product else "NOT_FOUND")

    def _store_id(self, current_user: User) -> UUID:
        if current_user.store_id is None:
            raise bad_request("Current user is not assigned to a store")
        return current_user.store_id

    def _find_category(self, name: Optional[str]) -> Optional[Category]:
        if not name:
            return None
        return self.db.query(Category).filter(func.lower(Category.name) == name.strip().lower()).first()

    def _find_brand(self, category_id: UUID, name: Optional[str]) -> Optional[Brand]:
        if not category_id or not name:
            return None
        return self.db.query(Brand).filter(Brand.category_id == category_id, func.lower(Brand.name) == name.strip().lower()).first()

    def _get_or_create_category(self, name: Optional[str]) -> Optional[Category]:
        if not name:
            return None
        category = self._find_category(name)
        if category:
            return category
        category = Category(name=name.strip(), description="Created from invoice extraction")
        self.db.add(category)
        self.db.flush()
        return category

    def _get_or_create_brand(self, category_id: Optional[UUID], name: Optional[str]) -> Optional[Brand]:
        if not category_id or not name:
            return None
        brand = self._find_brand(category_id, name)
        if brand:
            return brand
        brand = Brand(category_id=category_id, name=name.strip(), description="Created from invoice extraction")
        self.db.add(brand)
        self.db.flush()
        return brand

    def _get_or_create_default_subcategory(self, category_id: UUID) -> SubCategory:
        subcategory = (
            self.db.query(SubCategory)
            .filter(SubCategory.category_id == category_id, func.lower(SubCategory.name) == "general")
            .first()
        )
        if subcategory:
            return subcategory
        subcategory = SubCategory(category_id=category_id, name="General", description="Default product group")
        self.db.add(subcategory)
        self.db.flush()
        return subcategory

    def _find_supplier(self, name: Optional[str]) -> Optional[Supplier]:
        if not name:
            return None
        return self.db.query(Supplier).filter(func.lower(Supplier.name) == name.strip().casefold(), Supplier.is_active.is_(True)).first()

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
        duplicate = self.repo.find_duplicate_invoice(store_id, purchase.supplier_id, purchase.supplier_name, purchase.invoice_number, purchase.id)
        if duplicate:
            raise conflict("This invoice number already exists for this supplier.")

    def _duplicate_warning(self, purchase: Purchase, store_id: UUID) -> Optional[str]:
        duplicate = self.repo.find_duplicate_invoice(store_id, purchase.supplier_id, purchase.supplier_name, purchase.invoice_number, purchase.id)
        return "This invoice number already exists for this supplier." if duplicate else None

    @staticmethod
    def _line_total(item: PurchaseItem) -> Decimal:
        return (Decimal(item.quantity) * item.purchase_price) - item.discount + item.tax_amount

    def _recalculate_totals(self, purchase: Purchase) -> None:
        for item in purchase.items:
            item.line_total = self._line_total(item)
        purchase.subtotal = sum((Decimal(item.quantity) * item.purchase_price for item in purchase.items), Decimal("0"))
        purchase.discount = sum((item.discount for item in purchase.items), Decimal("0"))
        purchase.tax_amount = sum((item.tax_amount for item in purchase.items), Decimal("0"))
        purchase.total_amount = purchase.subtotal - purchase.discount + purchase.tax_amount + purchase.packaging_amount + purchase.freight_amount + purchase.round_off
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
