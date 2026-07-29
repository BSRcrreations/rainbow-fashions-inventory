from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from math import ceil
from typing import Literal, Optional
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.exceptions import bad_request, conflict, not_found
from app.models.brand import Brand
from app.models.category import Category
from app.models.enums import SaleStatus, StockMovementType
from app.models.product import Product
from app.models.product_barcode import ProductBarcode
from app.models.product_inventory import ProductInventory
from app.models.product_variant import InventoryCostLot, ProductVariant
from app.models.sale import Sale, SaleAudit, SaleItem, SaleReturn, SaleReturnItem
from app.models.stock_history import StockHistory
from app.models.user import User
from app.repositories.sale import SaleRepository
from app.schemas.sale import SaleCatalogProduct, SaleCatalogVariant, SaleCreate, SaleListResponse, SaleReturnCreate, SaleUpdate, SaleVoidRequest, SalesDashboardResponse, SalesMetric


BUSINESS_TIMEZONE = ZoneInfo("Asia/Kolkata")


class SaleService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SaleRepository(db)

    def create(self, payload: SaleCreate, current_user: User) -> Sale:
        if all(item.product_variant_id is not None for item in payload.items):
            return self._create_variant_sale(payload, current_user)
        store_id = self._store_id(current_user)
        invoice_number = payload.invoice_number or self._generate_invoice_number()
        if self.repo.get_by_invoice(invoice_number, store_id):
            raise conflict("Invoice number already exists")
        prepared = self._prepare_items(payload.items, store_id)
        subtotal, cost_amount, total_amount = self._totals(prepared, payload.discount)
        sale = Sale(
            store_id=store_id,
            invoice_number=invoice_number,
            customer_name=payload.customer_name,
            payment_mode=payload.payment_mode,
            cashier_id=current_user.id,
            subtotal=subtotal,
            discount=payload.discount,
            total_amount=total_amount,
            cost_amount=cost_amount,
            profit_amount=total_amount - cost_amount,
            sale_date=payload.sale_date or datetime.now(timezone.utc),
        )
        self.db.add(sale)
        self.db.flush()

        for product, inventory, quantity, unit_price, line_total in prepared:
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                product_name=product.name,
                quantity=quantity,
                unit_price=unit_price,
                unit_cost=product.purchase_price,
                line_total=line_total,
                sku_snapshot=product.sku,
                barcode_snapshot=product.barcode,
                size_snapshot=product.size,
                color_snapshot=product.color,
            )
            self.db.add(sale_item)
            self.db.flush()
            self._adjust_stock(product, inventory, -quantity, StockMovementType.SALE, invoice_number, sale, sale_item, current_user)

        self.db.commit()
        return self.get(sale.id, current_user)

    def catalog(self, search: Optional[str], current_user: User) -> list[SaleCatalogProduct]:
        store_id = self._store_id(current_user)
        query = (
            self.db.query(ProductVariant)
            .join(Product)
            .options(joinedload(ProductVariant.product).joinedload(Product.category), joinedload(ProductVariant.product).joinedload(Product.brand))
            .filter(ProductVariant.store_id == store_id, ProductVariant.is_active.is_(True), Product.is_active.is_(True))
        )
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            query = query.filter(or_(Product.name.ilike(pattern), ProductVariant.internal_sku.ilike(pattern), ProductVariant.manufacturer_sku.ilike(pattern), ProductVariant.barcode.ilike(pattern), ProductVariant.size.ilike(pattern), ProductVariant.style_code.ilike(pattern)))
        grouped: dict[UUID, SaleCatalogProduct] = {}
        for variant in query.order_by(Product.name, ProductVariant.size, ProductVariant.mrp).all():
            product = variant.product
            group = grouped.setdefault(product.id, SaleCatalogProduct(product_id=product.id, name=product.name, category_name=product.category.name if product.category else None, brand_name=product.brand.name if product.brand else None, total_available_stock=0))
            group.variants.append(self._catalog_variant(variant))
            group.total_available_stock += variant.current_stock
        return list(grouped.values())

    def variant_by_barcode(self, barcode: str, current_user: User) -> SaleCatalogVariant:
        normalized = barcode.strip()
        if not normalized:
            raise bad_request("Barcode is required")
        store_id = self._store_id(current_user)
        barcode_mapping = self.db.query(ProductBarcode).filter(ProductBarcode.store_id == store_id, func.lower(ProductBarcode.barcode) == normalized.lower(), ProductBarcode.active.is_(True)).first()
        if barcode_mapping:
            variant = (
                self.db.query(ProductVariant)
                .filter(
                    ProductVariant.store_id == store_id,
                    ProductVariant.id == barcode_mapping.product_variant_id,
                )
                .first()
            )
        else:
            variant = (
                self.db.query(ProductVariant)
                .filter(
                    ProductVariant.store_id == store_id,
                    func.lower(ProductVariant.barcode) == normalized.lower(),
                )
                .first()
            )
        if not variant:
            raise not_found("Product variant for this barcode")
        return self._catalog_variant(variant)

    def _create_variant_sale(self, payload: SaleCreate, current_user: User) -> Sale:
        store_id = self._store_id(current_user)
        invoice_number = payload.invoice_number or self._generate_invoice_number()
        if self.repo.get_by_invoice(invoice_number, store_id):
            raise conflict("Invoice number already exists")
        variant_ids = [item.product_variant_id for item in payload.items]
        if len(variant_ids) != len(set(variant_ids)):
            raise bad_request("A variant can appear only once in a sale")
        prepared: list[tuple[Product, ProductVariant, int, Decimal, Decimal, Decimal, list[tuple[Optional[InventoryCostLot], int, Decimal]]]] = []
        for request in sorted(payload.items, key=lambda item: str(item.product_variant_id)):
            variant = (
                self.db.query(ProductVariant)
                .options(joinedload(ProductVariant.product))
                .filter(ProductVariant.id == request.product_variant_id, ProductVariant.store_id == store_id)
                .with_for_update(of=ProductVariant)
                .first()
            )
            if not variant or not variant.product.is_active or not variant.is_active:
                raise bad_request("The selected product variant is unavailable")
            if variant.current_stock < request.quantity:
                raise bad_request(f"Insufficient stock for {variant.product.name} {variant.size or ''}; {variant.current_stock} available")
            price = request.unit_price if request.unit_price is not None else variant.selling_price
            if request.unit_price is not None and request.unit_price != variant.selling_price:
                role = getattr(current_user.role, "value", str(current_user.role))
                if role == "CASHIER":
                    raise bad_request("Only a manager or owner can override the configured selling price")
                if role == "MANAGER" and variant.mrp is not None and request.unit_price > variant.mrp:
                    raise bad_request("Manager price override cannot exceed MRP")
            lots = (
                self.db.query(InventoryCostLot)
                .filter(InventoryCostLot.product_variant_id == variant.id, InventoryCostLot.remaining_quantity > 0)
                .order_by(InventoryCostLot.received_date, InventoryCostLot.created_at, InventoryCostLot.id)
                .with_for_update()
                .all()
            )
            remaining = request.quantity
            allocations: list[tuple[Optional[InventoryCostLot], int, Decimal]] = []
            for lot in lots:
                quantity = min(remaining, lot.remaining_quantity)
                if quantity:
                    allocations.append((lot, quantity, lot.effective_unit_cost))
                    remaining -= quantity
                if not remaining:
                    break
            if remaining:
                allocations.append((None, remaining, variant.average_cost))
            cost = sum((unit_cost * quantity for _, quantity, unit_cost in allocations), Decimal("0"))
            prepared.append((variant.product, variant, request.quantity, price, price * request.quantity, cost, allocations))
        subtotal = sum((line_total for _, _, _, _, line_total, _, _ in prepared), Decimal("0"))
        if payload.discount > subtotal:
            raise bad_request("Discount cannot exceed subtotal")
        total = subtotal - payload.discount
        cost_amount = sum((cost for _, _, _, _, _, cost, _ in prepared), Decimal("0"))
        sale = Sale(store_id=store_id, invoice_number=invoice_number, customer_name=payload.customer_name, payment_mode=payload.payment_mode, cashier_id=current_user.id, subtotal=subtotal, discount=payload.discount, total_amount=total, cost_amount=cost_amount, profit_amount=total - cost_amount, sale_date=payload.sale_date or datetime.now(timezone.utc))
        self.db.add(sale)
        self.db.flush()
        for product, variant, quantity, price, line_total, cost, allocations in prepared:
            sale_item = SaleItem(sale_id=sale.id, product_id=product.id, product_variant_id=variant.id, product_name=product.name, quantity=quantity, unit_price=price, unit_cost=(cost / quantity), line_total=line_total, sku_snapshot=variant.internal_sku, barcode_snapshot=variant.barcode, size_snapshot=variant.size, color_snapshot=variant.color, style_snapshot=variant.style_code, mrp_snapshot=variant.mrp)
            self.db.add(sale_item)
            self.db.flush()
            product, inventory = self._locked_product_inventory(product.id, store_id)
            before_variant_stock = variant.current_stock
            for lot, allocation_quantity, unit_cost in allocations:
                if lot:
                    lot.remaining_quantity -= allocation_quantity
                variant.current_stock -= allocation_quantity
                self.db.add(StockHistory(product_id=product.id, product_variant_id=variant.id, purchase_cost_lot_id=lot.id if lot else None, store_id=store_id, movement_type=StockMovementType.SALE, qty=allocation_quantity, before_stock=before_variant_stock, after_stock=variant.current_stock, reference=invoice_number, sale_id=sale.id, sale_item_id=sale_item.id, created_by=current_user.id, unit_cost=unit_cost))
                before_variant_stock = variant.current_stock
            inventory.current_stock -= quantity
            product.current_stock = max(0, product.current_stock - quantity)
        self.db.add(SaleAudit(sale_id=sale.id, action="COMPLETED", reason=None, performed_by=current_user.id, before_data=None, after_data={"variant_sale": True, "total_amount": str(total)}))
        self.db.commit()
        return self.get(sale.id, current_user)

    @staticmethod
    def _catalog_variant(variant: ProductVariant) -> SaleCatalogVariant:
        return SaleCatalogVariant(variant_id=variant.id, size=variant.size, color=variant.color, style_code=variant.style_code, sku=variant.internal_sku, barcode=variant.barcode, mrp=variant.mrp, selling_price=variant.selling_price, available_stock=variant.current_stock, classification_review_required=variant.classification_review_required, is_active=variant.is_active)

    def get(self, sale_id: UUID, current_user: User) -> Sale:
        sale = self.repo.get_detail(sale_id, self._store_id(current_user))
        if not sale:
            raise not_found("Sale")
        return sale

    def update(self, sale_id: UUID, payload: SaleUpdate, current_user: User) -> Sale:
        store_id = self._store_id(current_user)
        sale = self._locked_sale(sale_id, store_id)
        if sale.status in {SaleStatus.VOIDED, SaleStatus.RETURNED}:
            raise bad_request("This sale cannot be edited")
        self._validate_version(sale, payload.version)
        before = self._audit_snapshot(sale)
        product_ids = [item.product_id for item in payload.items]
        if len(product_ids) != len(set(product_ids)):
            raise bad_request("A product can appear only once in a sale")
        prepared = self._prepare_items(payload.items, store_id, validate_stock=False)
        subtotal, cost_amount, total_amount = self._totals(prepared, payload.discount)
        old_items = {item.product_id: item for item in sale.items}
        new_items = {product.id: (product, inventory, quantity, price, line_total) for product, inventory, quantity, price, line_total in prepared}
        for product_id in sorted(set(old_items) | set(new_items), key=str):
            old = old_items.get(product_id)
            new = new_items.get(product_id)
            old_quantity = old.quantity if old else 0
            new_quantity = new[2] if new else 0
            delta = old_quantity - new_quantity
            if delta:
                product, inventory = (new[0], new[1]) if new else self._locked_product_inventory(product_id, store_id)
                movement = StockMovementType.SALE_EDIT_RETURN if delta > 0 else StockMovementType.SALE_EDIT_DECREASE
                self._adjust_stock(product, inventory, delta, movement, f"{sale.invoice_number} sale edit", sale, old, current_user)
        self.db.query(SaleItem).filter(SaleItem.sale_id == sale.id).delete(synchronize_session=False)
        self.db.flush()
        for product, _, quantity, unit_price, line_total in prepared:
            self.db.add(SaleItem(sale_id=sale.id, product_id=product.id, product_name=product.name, quantity=quantity, unit_price=unit_price, unit_cost=product.purchase_price, line_total=line_total, sku_snapshot=product.sku, barcode_snapshot=product.barcode, size_snapshot=product.size, color_snapshot=product.color))
        sale.customer_name = payload.customer_name
        sale.payment_mode = payload.payment_mode
        sale.subtotal, sale.discount, sale.total_amount, sale.cost_amount = subtotal, payload.discount, total_amount, cost_amount
        sale.profit_amount = total_amount - cost_amount
        sale.status, sale.version, sale.edit_reason, sale.edited_by, sale.edited_at = SaleStatus.EDITED, sale.version + 1, payload.edit_reason, current_user.id, datetime.now(timezone.utc)
        self.db.add(SaleAudit(sale_id=sale.id, action="EDITED", reason=payload.edit_reason, performed_by=current_user.id, before_data=before, after_data={"total_amount": str(total_amount), "version": sale.version}))
        self.db.commit()
        return self.get(sale.id, current_user)

    def void(self, sale_id: UUID, payload: SaleVoidRequest, current_user: User) -> Sale:
        store_id = self._store_id(current_user)
        sale = self._locked_sale(sale_id, store_id)
        if sale.status == SaleStatus.VOIDED:
            raise bad_request("Sale is already voided")
        self._validate_version(sale, payload.version)
        before = self._audit_snapshot(sale)
        returned = self._returned_quantities(sale)
        for item in sale.items:
            quantity = item.quantity - returned.get(item.id, 0)
            if quantity:
                self._restore_sale_item_stock(item, quantity, StockMovementType.SALE_VOID, f"{sale.invoice_number} void", sale, current_user)
        sale.status, sale.version, sale.void_reason, sale.voided_by, sale.voided_at = SaleStatus.VOIDED, sale.version + 1, payload.reason, current_user.id, datetime.now(timezone.utc)
        self.db.add(SaleAudit(sale_id=sale.id, action="VOIDED", reason=payload.reason, performed_by=current_user.id, before_data=before, after_data={"status": "VOIDED", "version": sale.version}))
        self.db.commit()
        return self.get(sale.id, current_user)

    def create_return(self, sale_id: UUID, payload: SaleReturnCreate, current_user: User) -> SaleReturn:
        store_id = self._store_id(current_user)
        sale = self._locked_sale(sale_id, store_id)
        if sale.status == SaleStatus.VOIDED:
            raise bad_request("Voided sales cannot be returned")
        requested_ids = [item.sale_item_id for item in payload.items]
        if len(requested_ids) != len(set(requested_ids)):
            raise bad_request("A sale item can appear only once in a return")
        item_map = {item.id: item for item in sale.items}
        if not set(requested_ids).issubset(item_map):
            raise bad_request("One or more items do not belong to this sale")
        returned = self._returned_quantities(sale)
        sale_return = SaleReturn(sale_id=sale.id, store_id=store_id, reason=payload.reason, refund_method=payload.refund_method or sale.payment_mode, refund_amount=Decimal("0"), created_by=current_user.id)
        self.db.add(sale_return)
        refund = Decimal("0")
        for request in payload.items:
            item = item_map[request.sale_item_id]
            if request.quantity > item.quantity - returned.get(item.id, 0):
                raise bad_request(f"Return quantity exceeds remaining quantity for {item.product_name}")
            amount = item.unit_price * request.quantity
            refund += amount
            self.db.add(SaleReturnItem(sale_return=sale_return, sale_item_id=item.id, quantity=request.quantity, refund_amount=amount))
            self._restore_sale_item_stock(item, request.quantity, StockMovementType.CUSTOMER_RETURN, f"{sale.invoice_number} customer return", sale, current_user)
        sale_return.refund_amount = refund
        self.db.flush()
        all_returned = all(item.quantity <= returned.get(item.id, 0) + sum(req.quantity for req in payload.items if req.sale_item_id == item.id) for item in sale.items)
        sale.status, sale.version = (SaleStatus.RETURNED if all_returned else SaleStatus.PARTIALLY_RETURNED), sale.version + 1
        self.db.add(SaleAudit(sale_id=sale.id, action="RETURNED", reason=payload.reason, performed_by=current_user.id, before_data=None, after_data={"refund_amount": str(refund), "status": sale.status.value}))
        self.db.commit()
        return sale_return

    def list_paginated(
        self,
        page: int = 1,
        page_size: int = 25,
        search: Optional[str] = None,
        payment_mode: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        invoice_number: Optional[str] = None,
        customer_name: Optional[str] = None,
        cashier_name: Optional[str] = None,
        status_filter: Optional[str] = None,
        current_user: Optional[User] = None,
        sort: str = "newest",
    ) -> SaleListResponse:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        start_at, end_at = self._optional_bounds(start_date, end_date)
        if current_user is None:
            raise bad_request("Current user is required")
        items, total = self.repo.list_paginated(page, page_size, search, payment_mode, start_at, end_at, invoice_number, customer_name, cashier_name, status_filter, self._store_id(current_user), sort)
        return SaleListResponse(
            items=items,
            meta={
                "page": page,
                "page_size": page_size,
                "total_records": total,
                "total_pages": ceil(total / page_size) if total else 1,
            },
        )

    def dashboard(
        self,
        preset: Literal["today", "yesterday", "week", "month", "custom"] = "today",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        current_user: Optional[User] = None,
    ) -> SalesDashboardResponse:
        if current_user is None:
            raise bad_request("Current user is required")
        store_id = self._store_id(current_user)
        today = datetime.now(BUSINESS_TIMEZONE).date()
        selected_start, selected_end = self._resolve_range(preset, start_date, end_date, today)
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        trend = self._trend(selected_start, selected_end, store_id)
        selected_start_at, selected_end_at = self._bounds(selected_start, selected_end)

        return SalesDashboardResponse(
            range_start=selected_start,
            range_end=selected_end,
            selected=self._metric(selected_start, selected_end, store_id),
            today=self._metric(today, today, store_id),
            yesterday=self._metric(today - timedelta(days=1), today - timedelta(days=1), store_id),
            week=self._metric(week_start, today, store_id),
            month=self._metric(month_start, today, store_id),
            total_revenue=self.db.query(func.coalesce(func.sum(Sale.total_amount), 0)).filter(Sale.store_id == store_id, Sale.status != SaleStatus.VOIDED).scalar() or Decimal("0"),
            collection=self._collection(selected_start, selected_end, store_id),
            inventory_value=(
                self.db.query(func.coalesce(func.sum(Product.purchase_price * Product.current_stock), 0))
                .join(ProductInventory, ProductInventory.product_id == Product.id).filter(Product.is_active.is_(True), ProductInventory.store_id == store_id)
                .scalar()
                or Decimal("0")
            ),
            total_stock=(
                self.db.query(func.coalesce(func.sum(ProductInventory.current_stock), 0))
                .join(Product, ProductInventory.product_id == Product.id).filter(Product.is_active.is_(True), ProductInventory.store_id == store_id)
                .scalar()
                or 0
            ),
            total_products=self.db.query(func.count(Product.id)).filter(Product.is_active.is_(True)).scalar() or 0,
            trend=trend,
            top_categories=self._ranking("category", selected_start_at, selected_end_at, store_id),
            top_brands=self._ranking("brand", selected_start_at, selected_end_at, store_id),
            top_products=self._ranking("product", selected_start_at, selected_end_at, store_id),
            recent_sales=(
                self.db.query(Sale)
                .options(joinedload(Sale.cashier), joinedload(Sale.items))
                .filter(Sale.store_id == store_id, Sale.status != SaleStatus.VOIDED, Sale.sale_date.between(selected_start_at, selected_end_at))
                .order_by(Sale.sale_date.desc())
                .limit(8)
                .all()
            ),
            low_stock=[
                {"id": product.id, "name": product.name, "current_stock": product.current_stock, "minimum_stock": product.minimum_stock}
                for product in self.db.query(Product).join(ProductInventory).filter(ProductInventory.store_id == store_id, ProductInventory.current_stock > 0, ProductInventory.current_stock <= ProductInventory.minimum_stock, Product.is_active.is_(True)).order_by(ProductInventory.current_stock).limit(8).all()
            ],
            out_of_stock=[
                {"id": product.id, "name": product.name, "current_stock": product.current_stock, "minimum_stock": product.minimum_stock}
                for product in self.db.query(Product).join(ProductInventory).filter(ProductInventory.store_id == store_id, ProductInventory.current_stock == 0, Product.is_active.is_(True)).order_by(Product.name).limit(8).all()
            ],
        )

    def _collection(self, start_date: date, end_date: date, store_id: UUID) -> dict:
        start_at, end_at = self._bounds(start_date, end_date)
        rows = (
            self.db.query(Sale.payment_mode, func.coalesce(func.sum(Sale.total_amount), 0))
            .filter(Sale.store_id == store_id, Sale.status != SaleStatus.VOIDED, Sale.sale_date.between(start_at, end_at))
            .group_by(Sale.payment_mode)
            .all()
        )
        amounts = {str(payment_mode).upper(): amount for payment_mode, amount in rows}
        cash = amounts.get("CASH", Decimal("0"))
        upi = amounts.get("UPI", Decimal("0"))
        card = amounts.get("CARD", Decimal("0"))
        other = sum((amount for mode, amount in amounts.items() if mode not in {"CASH", "UPI", "CARD"}), Decimal("0"))
        return {"cash": cash, "upi": upi, "card": card, "other": other, "total": cash + upi + card + other}

    def export_xlsx(self, sales: list[Sale]) -> bytes:
        from openpyxl import Workbook

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Sales"
        sheet.append(["Invoice", "Date", "Customer", "Payment", "Cashier", "Subtotal", "Discount", "Total", "Profit"])
        for sale in sales:
            sheet.append([
                sale.invoice_number,
                sale.sale_date.isoformat(),
                sale.customer_name or "Walk-in",
                sale.payment_mode,
                sale.cashier.full_name if sale.cashier else "-",
                float(sale.subtotal),
                float(sale.discount),
                float(sale.total_amount),
                float(sale.profit_amount),
            ])
        output = BytesIO()
        workbook.save(output)
        return output.getvalue()

    def export_pdf(self, sales: list[Sale]) -> bytes:
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        except ImportError as exc:
            raise bad_request("PDF export requires reportlab to be installed") from exc

        output = BytesIO()
        document = SimpleDocTemplate(output, pagesize=landscape(A4), title="Rainbow Fashions Sales")
        styles = getSampleStyleSheet()
        rows = [["Invoice", "Date", "Customer", "Payment", "Cashier", "Total", "Profit"]]
        rows.extend([
            [
                sale.invoice_number,
                sale.sale_date.astimezone(BUSINESS_TIMEZONE).strftime("%d %b %Y %I:%M %p"),
                sale.customer_name or "Walk-in",
                sale.payment_mode,
                sale.cashier.full_name if sale.cashier else "-",
                f"Rs. {sale.total_amount:.2f}",
                f"Rs. {sale.profit_amount:.2f}",
            ]
            for sale in sales
        ])
        table = Table(rows, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dbe2ea")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        document.build([Paragraph("Rainbow Fashions Sales History", styles["Title"]), Spacer(1, 12), table])
        return output.getvalue()

    def export_records(
        self,
        search: Optional[str],
        payment_mode: Optional[str],
        start_date: Optional[date],
        end_date: Optional[date],
        invoice_number: Optional[str] = None,
        customer_name: Optional[str] = None,
        cashier_name: Optional[str] = None,
        status_filter: Optional[str] = None,
        current_user: Optional[User] = None,
    ) -> list[Sale]:
        start_at, end_at = self._optional_bounds(start_date, end_date)
        if current_user is None:
            raise bad_request("Current user is required")
        items, _ = self.repo.list_paginated(1, 10000, search, payment_mode, start_at, end_at, invoice_number, customer_name, cashier_name, status_filter, self._store_id(current_user))
        return items

    def _metric(self, start_date: date, end_date: date, store_id: UUID) -> SalesMetric:
        start_at, end_at = self._bounds(start_date, end_date)
        sales, profit, orders = (
            self.db.query(
                func.coalesce(func.sum(Sale.total_amount), 0),
                func.coalesce(func.sum(Sale.profit_amount), 0),
                func.count(Sale.id),
            )
            .filter(Sale.store_id == store_id, Sale.status != SaleStatus.VOIDED, Sale.sale_date.between(start_at, end_at))
            .one()
        )
        return SalesMetric(sales=sales, profit=profit, orders=orders)

    def _trend(self, start_date: date, end_date: date, store_id: UUID) -> list[dict]:
        start_at, end_at = self._bounds(start_date, end_date)
        day_expression = func.date(func.timezone(str(BUSINESS_TIMEZONE), Sale.sale_date))
        rows = (
            self.db.query(
                day_expression.label("day"),
                func.coalesce(func.sum(Sale.total_amount), 0),
                func.coalesce(func.sum(Sale.profit_amount), 0),
                func.count(Sale.id),
            )
            .filter(Sale.store_id == store_id, Sale.status != SaleStatus.VOIDED, Sale.sale_date.between(start_at, end_at))
            .group_by(day_expression)
            .order_by(day_expression)
            .all()
        )
        by_day = {row[0]: row[1:] for row in rows}
        result = []
        current = start_date
        while current <= end_date:
            values = by_day.get(current, (Decimal("0"), Decimal("0"), 0))
            result.append({"date": current, "sales": values[0], "profit": values[1], "orders": values[2]})
            current += timedelta(days=1)
        return result

    def _ranking(self, kind: str, start_at: datetime, end_at: datetime, store_id: UUID) -> list[dict]:
        if kind == "category":
            id_column, name_column = Category.id, Category.name
        elif kind == "brand":
            id_column, name_column = Brand.id, Brand.name
        else:
            id_column, name_column = Product.id, Product.name
        query = (
            self.db.query(
                id_column,
                name_column,
                func.coalesce(func.sum(SaleItem.quantity), 0),
                func.coalesce(func.sum(SaleItem.line_total), 0),
            )
            .join(Product, SaleItem.product_id == Product.id)
            .join(Sale, SaleItem.sale_id == Sale.id)
        )
        if kind == "category":
            query = query.join(Category, Product.category_id == Category.id)
        elif kind == "brand":
            query = query.join(Brand, Product.brand_id == Brand.id)
        rows = (
            query.filter(Sale.store_id == store_id, Sale.status != SaleStatus.VOIDED, Sale.sale_date.between(start_at, end_at))
            .group_by(id_column, name_column)
            .order_by(func.sum(SaleItem.quantity).desc())
            .limit(8)
            .all()
        )
        return [{"id": row[0], "name": row[1], "quantity": row[2], "revenue": row[3]} for row in rows]

    def _resolve_range(self, preset: str, start_date: Optional[date], end_date: Optional[date], today: date) -> tuple[date, date]:
        if preset == "yesterday":
            yesterday = today - timedelta(days=1)
            return yesterday, yesterday
        if preset == "week":
            return today - timedelta(days=today.weekday()), today
        if preset == "month":
            return today.replace(day=1), today
        if preset == "custom":
            if not start_date or not end_date:
                raise bad_request("Custom date range requires start_date and end_date")
            if start_date > end_date:
                raise bad_request("start_date cannot be after end_date")
            if (end_date - start_date).days > 366:
                raise bad_request("Date range cannot exceed 366 days")
            return start_date, end_date
        return today, today

    def _optional_bounds(self, start_date: Optional[date], end_date: Optional[date]) -> tuple[Optional[datetime], Optional[datetime]]:
        if start_date and end_date and start_date > end_date:
            raise bad_request("start_date cannot be after end_date")
        start_at = self._bounds(start_date, start_date)[0] if start_date else None
        end_at = self._bounds(end_date, end_date)[1] if end_date else None
        return start_at, end_at

    def _bounds(self, start_date: date, end_date: date) -> tuple[datetime, datetime]:
        start_local = datetime.combine(start_date, time.min, tzinfo=BUSINESS_TIMEZONE)
        end_local = datetime.combine(end_date, time.max, tzinfo=BUSINESS_TIMEZONE)
        return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)

    def _generate_invoice_number(self) -> str:
        date_part = datetime.now(BUSINESS_TIMEZONE).strftime("%Y%m%d")
        for _ in range(10):
            candidate = f"RF-{date_part}-{uuid4().hex[:6].upper()}"
            if not self.db.query(Sale).filter(Sale.invoice_number == candidate).first():
                return candidate
        raise conflict("Unable to generate invoice number")

    def list_audits(self, sale_id: UUID, current_user: User) -> list[SaleAudit]:
        return self.repo.list_audits(sale_id, self._store_id(current_user))

    def list_returns(self, sale_id: UUID, current_user: User) -> list[SaleReturn]:
        return self.repo.list_returns(sale_id, self._store_id(current_user))

    def _store_id(self, current_user: User) -> UUID:
        if current_user.store_id is None:
            raise bad_request("Current user is not assigned to a store")
        return current_user.store_id

    def _locked_sale(self, sale_id: UUID, store_id: UUID) -> Sale:
        sale = (
            self.db.query(Sale)
            .options(selectinload(Sale.items))
            .filter(Sale.id == sale_id, Sale.store_id == store_id)
            .with_for_update()
            .first()
        )
        if not sale:
            raise not_found("Sale")
        return sale

    def _locked_product_inventory(self, product_id: UUID, store_id: UUID) -> tuple[Product, ProductInventory]:
        product = self.db.query(Product).filter(Product.id == product_id, Product.store_id == store_id).with_for_update().first()
        if not product:
            raise not_found("Product")
        inventory = (
            self.db.query(ProductInventory)
            .filter(ProductInventory.product_id == product_id, ProductInventory.store_id == store_id)
            .with_for_update()
            .first()
        )
        if inventory is None:
            inventory = ProductInventory(product_id=product_id, store_id=store_id, current_stock=0, minimum_stock=product.minimum_stock)
            self.db.add(inventory)
            self.db.flush()
        return product, inventory

    def _prepare_items(self, items: list, store_id: UUID, validate_stock: bool = True) -> list[tuple[Product, ProductInventory, int, Decimal, Decimal]]:
        product_ids = [item.product_id for item in items]
        if len(product_ids) != len(set(product_ids)):
            raise bad_request("A product can appear only once in a sale")
        prepared = []
        for request in sorted(items, key=lambda item: str(item.product_id)):
            product, inventory = self._locked_product_inventory(request.product_id, store_id)
            if not product.is_active:
                raise bad_request(f"{product.name} is inactive")
            if validate_stock and inventory.current_stock < request.quantity:
                raise bad_request(f"Insufficient stock for {product.name}; {inventory.current_stock} available")
            unit_price = request.unit_price if request.unit_price is not None else product.selling_price
            prepared.append((product, inventory, request.quantity, unit_price, unit_price * request.quantity))
        return prepared

    def _totals(self, prepared: list[tuple[Product, ProductInventory, int, Decimal, Decimal]], discount: Decimal) -> tuple[Decimal, Decimal, Decimal]:
        subtotal = sum((line_total for _, _, _, _, line_total in prepared), Decimal("0"))
        if discount > subtotal:
            raise bad_request("Discount cannot exceed subtotal")
        cost = sum((product.purchase_price * quantity for product, _, quantity, _, _ in prepared), Decimal("0"))
        return subtotal, cost, subtotal - discount

    def _adjust_stock(
        self,
        product: Product,
        inventory: ProductInventory,
        delta: int,
        movement_type: StockMovementType,
        reference: str,
        sale: Sale,
        sale_item: Optional[SaleItem],
        current_user: User,
    ) -> None:
        before_stock = inventory.current_stock
        after_stock = before_stock + delta
        if after_stock < 0:
            raise bad_request(f"Insufficient stock for {product.name}; {before_stock} available")
        inventory.current_stock = after_stock
        # Product.current_stock remains a compatibility aggregate; store inventory is authoritative for sales.
        product.current_stock = max(0, product.current_stock + delta)
        self.db.add(StockHistory(product_id=product.id, store_id=inventory.store_id, movement_type=movement_type, qty=abs(delta), before_stock=before_stock, after_stock=after_stock, reference=reference, sale_id=sale.id, sale_item_id=sale_item.id if sale_item else None, created_by=current_user.id))

    def _restore_sale_item_stock(
        self,
        sale_item: SaleItem,
        quantity: int,
        movement_type: StockMovementType,
        reference: str,
        sale: Sale,
        current_user: User,
    ) -> None:
        """Restore a returned or voided item to its exact variant when available."""
        product, inventory = self._locked_product_inventory(sale_item.product_id, self._store_id(current_user))
        if not getattr(sale_item, "product_variant_id", None):
            self._adjust_stock(product, inventory, quantity, movement_type, reference, sale, sale_item, current_user)
            return
        variant = (
            self.db.query(ProductVariant)
            .filter(ProductVariant.id == sale_item.product_variant_id, ProductVariant.store_id == self._store_id(current_user))
            .with_for_update()
            .first()
        )
        if not variant:
            raise bad_request("The original product variant is no longer available for this return")
        before_variant_stock = variant.current_stock
        variant.current_stock += quantity
        inventory.current_stock += quantity
        product.current_stock += quantity
        lot = InventoryCostLot(
            store_id=self._store_id(current_user),
            product_variant_id=variant.id,
            received_quantity=quantity,
            remaining_quantity=quantity,
            unit_purchase_cost=sale_item.unit_cost,
            allocated_landed_cost=Decimal("0"),
            effective_unit_cost=sale_item.unit_cost,
            lot_reference=reference,
        )
        self.db.add(lot)
        self.db.flush()
        self.db.add(
            StockHistory(
                product_id=product.id,
                product_variant_id=variant.id,
                purchase_cost_lot_id=lot.id,
                unit_cost=sale_item.unit_cost,
                store_id=inventory.store_id,
                movement_type=movement_type,
                qty=quantity,
                before_stock=before_variant_stock,
                after_stock=variant.current_stock,
                reference=reference,
                sale_id=sale.id,
                sale_item_id=sale_item.id,
                created_by=current_user.id,
            )
        )

    def _validate_version(self, sale: Sale, version: int) -> None:
        if sale.version != version:
            raise conflict("This invoice was changed by another user. Reload it before saving.")

    def _returned_quantities(self, sale: Sale) -> dict[UUID, int]:
        rows = (
            self.db.query(SaleReturnItem.sale_item_id, func.coalesce(func.sum(SaleReturnItem.quantity), 0))
            .join(SaleReturn)
            .filter(SaleReturn.sale_id == sale.id)
            .group_by(SaleReturnItem.sale_item_id)
            .all()
        )
        return {sale_item_id: quantity for sale_item_id, quantity in rows}

    def _audit_snapshot(self, sale: Sale) -> dict:
        return {
            "status": sale.status.value,
            "version": sale.version,
            "customer_name": sale.customer_name,
            "payment_mode": sale.payment_mode,
            "subtotal": str(sale.subtotal),
            "discount": str(sale.discount),
            "total_amount": str(sale.total_amount),
            "items": [{"product_id": str(item.product_id), "quantity": item.quantity, "unit_price": str(item.unit_price)} for item in sale.items],
        }
