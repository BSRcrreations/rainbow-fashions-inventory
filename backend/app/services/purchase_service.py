from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import UploadFile
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.ai.factory import get_ocr_service
from app.ai.invoice_parser import InvoiceParser
from app.core.exceptions import bad_request, not_found
from app.models.brand import Brand
from app.models.category import Category
from app.models.enums import PricingType, PurchaseStatus, StockMovementType
from app.models.product import Product
from app.models.product_inventory import ProductInventory
from app.models.subcategory import SubCategory
from app.models.purchase import Purchase
from app.models.purchase_item import PurchaseItem
from app.models.stock_history import StockHistory
from app.models.supplier import Supplier
from app.models.user import User
from app.repositories.product import ProductRepository
from app.repositories.purchase import PurchaseRepository
from app.schemas.purchase import ExtractedInvoice, PurchaseItemReview, PurchaseReviewUpdate, PurchaseUploadResponse
from app.services.file_service import FileService


class PurchaseService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PurchaseRepository(db)
        self.product_repo = ProductRepository(db)

    async def upload_invoice(self, file: UploadFile, current_user: User) -> PurchaseUploadResponse:
        uploaded_file = await FileService(self.db).save_invoice_file(file, current_user.id)
        raw_text = get_ocr_service().extract_text(Path(uploaded_file.storage_path))
        extracted_invoice = InvoiceParser().parse(raw_text)
        review_items = self._build_review_items(extracted_invoice)
        supplier = self._get_or_create_supplier(extracted_invoice.supplier)

        purchase = Purchase(
            store_id=current_user.store_id,
            supplier_id=supplier.id if supplier else None,
            uploaded_file_id=uploaded_file.id,
            invoice_number=extracted_invoice.invoice_number,
            invoice_date=extracted_invoice.date,
            supplier_name=extracted_invoice.supplier,
            status=PurchaseStatus.DRAFT,
            extracted_payload=jsonable_encoder(extracted_invoice),
            reviewed_payload=jsonable_encoder({"items": review_items}),
            total_amount=extracted_invoice.total_amount,
            created_by=current_user.id,
        )
        self.repo.add(purchase)
        self.db.commit()
        purchase = self.repo.get_with_items(purchase.id)
        if not purchase:
            raise not_found("Purchase")
        return PurchaseUploadResponse(purchase=purchase, extracted_invoice=extracted_invoice, review_items=review_items)

    def list(self, skip: int = 0, limit: int = 50) -> list[Purchase]:
        return self.repo.list_recent(skip, limit)

    def get(self, purchase_id: UUID) -> Purchase:
        purchase = self.repo.get_with_items(purchase_id)
        if not purchase:
            raise not_found("Purchase")
        return purchase

    def update_review(self, purchase_id: UUID, payload: PurchaseReviewUpdate) -> Purchase:
        purchase = self.get(purchase_id)
        if purchase.status == PurchaseStatus.CONFIRMED:
            raise bad_request("Confirmed purchases cannot be edited")
        purchase.supplier_name = payload.supplier_name
        purchase.invoice_number = payload.invoice_number
        purchase.invoice_date = payload.invoice_date
        purchase.reviewed_payload = jsonable_encoder(payload)
        purchase.total_amount = sum((item.line_total for item in payload.items), Decimal("0"))
        purchase.status = PurchaseStatus.REVIEWED

        purchase.items.clear()
        self.db.flush()
        for item in payload.items:
            purchase.items.append(self._create_purchase_item(purchase.id, item))

        self.db.commit()
        return self.get(purchase_id)

    def confirm(self, purchase_id: UUID, current_user: User) -> Purchase:
        purchase = self.get(purchase_id)
        if purchase.status == PurchaseStatus.CONFIRMED:
            raise bad_request("Purchase is already confirmed")

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

        purchase.status = PurchaseStatus.CONFIRMED
        purchase.confirmed_by = current_user.id
        purchase.confirmed_at = datetime.now(timezone.utc)
        self.db.commit()
        return self.get(purchase.id)

    def _build_review_items(self, extracted_invoice: ExtractedInvoice) -> list[PurchaseItemReview]:
        review_items: list[PurchaseItemReview] = []
        for item in extracted_invoice.items:
            matched = self._match_product(item.brand, item.category, item.product_name, item.size, item.color)
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
                    size=item.size,
                    color=item.color,
                    quantity=item.quantity,
                    purchase_price=item.purchase_price,
                    mrp=item.mrp,
                    line_total=item.total_amount,
                    confidence=item.confidence,
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
                    size=item.size,
                    color=item.color,
                    quantity=item.quantity,
                    purchase_price=item.purchase_price,
                    mrp=item.mrp,
                    line_total=item.line_total,
                    confidence=item.confidence,
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
            size=item.size.strip(),
            color=item.color.strip(),
            quantity=item.quantity,
            purchase_price=item.purchase_price,
            mrp=item.mrp,
            line_total=item.line_total,
            confidence=item.confidence,
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

        duplicate = self.product_repo.get_duplicate(category.id, subcategory.id, brand.id, item.product_name, item.size, item.color)
        if duplicate:
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

    def _match_product(self, brand: Optional[str], category: Optional[str], name: str, size: str, color: str) -> Optional[Product]:
        query = self.db.query(Product).join(Product.brand).join(Product.category).filter(
            func.lower(Product.name) == name.strip().lower(),
            func.lower(Product.size) == size.strip().lower(),
            func.lower(Product.color) == color.strip().lower(),
        )
        if brand:
            query = query.filter(func.lower(Brand.name) == brand.strip().lower())
        if category:
            query = query.filter(func.lower(Category.name) == category.strip().lower())
        return query.first()

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

    def _get_or_create_supplier(self, name: Optional[str]) -> Optional[Supplier]:
        if not name:
            return None
        supplier = self.db.query(Supplier).filter(func.lower(Supplier.name) == name.strip().lower()).first()
        if supplier:
            return supplier
        supplier = Supplier(name=name.strip())
        self.db.add(supplier)
        self.db.flush()
        return supplier
