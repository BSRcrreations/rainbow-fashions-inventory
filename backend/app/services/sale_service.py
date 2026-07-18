from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from math import ceil
from typing import Literal, Optional
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import bad_request, conflict, not_found
from app.models.brand import Brand
from app.models.category import Category
from app.models.enums import StockMovementType
from app.models.product import Product
from app.models.product_inventory import ProductInventory
from app.models.sale import Sale, SaleItem
from app.models.stock_history import StockHistory
from app.models.user import User
from app.repositories.sale import SaleRepository
from app.schemas.sale import SaleCreate, SaleListResponse, SalesDashboardResponse, SalesMetric


BUSINESS_TIMEZONE = ZoneInfo("Asia/Kolkata")


class SaleService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SaleRepository(db)

    def create(self, payload: SaleCreate, current_user: User) -> Sale:
        if current_user.store_id is None:
            raise bad_request("Current user is not assigned to a store")
        invoice_number = payload.invoice_number or self._generate_invoice_number()
        if self.repo.get_by_invoice(invoice_number):
            raise conflict("Invoice number already exists")

        product_ids = [item.product_id for item in payload.items]
        if len(product_ids) != len(set(product_ids)):
            raise bad_request("A product can appear only once in a sale")
        products = (
            self.db.query(Product)
            .filter(Product.id.in_(product_ids))
            .with_for_update()
            .all()
        )
        product_map = {product.id: product for product in products}
        if len(product_map) != len(product_ids):
            raise not_found("One or more products")

        subtotal = Decimal("0")
        cost_amount = Decimal("0")
        prepared: list[tuple[Product, int, Decimal, Decimal]] = []
        for requested in payload.items:
            product = product_map[requested.product_id]
            if not product.is_active:
                raise bad_request(f"{product.name} is inactive")
            if product.current_stock < requested.quantity:
                raise bad_request(f"Insufficient stock for {product.name}; {product.current_stock} available")
            unit_price = requested.unit_price if requested.unit_price is not None else product.selling_price
            line_total = unit_price * requested.quantity
            subtotal += line_total
            cost_amount += product.purchase_price * requested.quantity
            prepared.append((product, requested.quantity, unit_price, line_total))

        if payload.discount > subtotal:
            raise bad_request("Discount cannot exceed subtotal")
        total_amount = subtotal - payload.discount
        sale = Sale(
            store_id=current_user.store_id,
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

        for product, quantity, unit_price, line_total in prepared:
            before_stock = product.current_stock
            product.current_stock -= quantity
            sale_item = SaleItem(
                sale_id=sale.id,
                product_id=product.id,
                product_name=product.name,
                quantity=quantity,
                unit_price=unit_price,
                unit_cost=product.purchase_price,
                line_total=line_total,
            )
            self.db.add(sale_item)
            self.db.flush()
            inventory = (
                self.db.query(ProductInventory)
                .filter(ProductInventory.product_id == product.id, ProductInventory.store_id == current_user.store_id)
                .first()
            )
            if inventory:
                inventory.current_stock = product.current_stock
            else:
                self.db.add(
                    ProductInventory(
                        product_id=product.id,
                        store_id=current_user.store_id,
                        current_stock=product.current_stock,
                        minimum_stock=product.minimum_stock,
                    )
                )
            self.db.add(
                StockHistory(
                    product_id=product.id,
                    store_id=current_user.store_id,
                    movement_type=StockMovementType.SALE,
                    qty=quantity,
                    before_stock=before_stock,
                    after_stock=product.current_stock,
                    reference=invoice_number,
                    sale_id=sale.id,
                    sale_item_id=sale_item.id,
                    created_by=current_user.id,
                )
            )

        self.db.commit()
        return self.get(sale.id)

    def get(self, sale_id: UUID) -> Sale:
        sale = self.repo.get_detail(sale_id)
        if not sale:
            raise not_found("Sale")
        return sale

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
    ) -> SaleListResponse:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        start_at, end_at = self._optional_bounds(start_date, end_date)
        items, total = self.repo.list_paginated(page, page_size, search, payment_mode, start_at, end_at, invoice_number, customer_name, cashier_name)
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
    ) -> SalesDashboardResponse:
        today = datetime.now(BUSINESS_TIMEZONE).date()
        selected_start, selected_end = self._resolve_range(preset, start_date, end_date, today)
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)
        trend = self._trend(selected_start, selected_end)
        selected_start_at, selected_end_at = self._bounds(selected_start, selected_end)

        return SalesDashboardResponse(
            range_start=selected_start,
            range_end=selected_end,
            selected=self._metric(selected_start, selected_end),
            today=self._metric(today, today),
            yesterday=self._metric(today - timedelta(days=1), today - timedelta(days=1)),
            week=self._metric(week_start, today),
            month=self._metric(month_start, today),
            total_revenue=self.db.query(func.coalesce(func.sum(Sale.total_amount), 0)).scalar() or Decimal("0"),
            collection=self._collection(selected_start, selected_end),
            inventory_value=(
                self.db.query(func.coalesce(func.sum(Product.purchase_price * Product.current_stock), 0))
                .filter(Product.is_active.is_(True))
                .scalar()
                or Decimal("0")
            ),
            total_stock=(
                self.db.query(func.coalesce(func.sum(Product.current_stock), 0))
                .filter(Product.is_active.is_(True))
                .scalar()
                or 0
            ),
            total_products=self.db.query(func.count(Product.id)).filter(Product.is_active.is_(True)).scalar() or 0,
            trend=trend,
            top_categories=self._ranking("category", selected_start_at, selected_end_at),
            top_brands=self._ranking("brand", selected_start_at, selected_end_at),
            top_products=self._ranking("product", selected_start_at, selected_end_at),
            recent_sales=(
                self.db.query(Sale)
                .options(joinedload(Sale.cashier), joinedload(Sale.items))
                .filter(Sale.sale_date.between(selected_start_at, selected_end_at))
                .order_by(Sale.sale_date.desc())
                .limit(8)
                .all()
            ),
            low_stock=[
                {"id": product.id, "name": product.name, "current_stock": product.current_stock, "minimum_stock": product.minimum_stock}
                for product in self.db.query(Product).filter(Product.current_stock > 0, Product.current_stock <= Product.minimum_stock, Product.is_active.is_(True)).order_by(Product.current_stock).limit(8).all()
            ],
            out_of_stock=[
                {"id": product.id, "name": product.name, "current_stock": product.current_stock, "minimum_stock": product.minimum_stock}
                for product in self.db.query(Product).filter(Product.current_stock == 0, Product.is_active.is_(True)).order_by(Product.name).limit(8).all()
            ],
        )

    def _collection(self, start_date: date, end_date: date) -> dict:
        start_at, end_at = self._bounds(start_date, end_date)
        rows = (
            self.db.query(Sale.payment_mode, func.coalesce(func.sum(Sale.total_amount), 0))
            .filter(Sale.sale_date.between(start_at, end_at))
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
    ) -> list[Sale]:
        start_at, end_at = self._optional_bounds(start_date, end_date)
        items, _ = self.repo.list_paginated(1, 10000, search, payment_mode, start_at, end_at, invoice_number, customer_name, cashier_name)
        return items

    def _metric(self, start_date: date, end_date: date) -> SalesMetric:
        start_at, end_at = self._bounds(start_date, end_date)
        sales, profit, orders = (
            self.db.query(
                func.coalesce(func.sum(Sale.total_amount), 0),
                func.coalesce(func.sum(Sale.profit_amount), 0),
                func.count(Sale.id),
            )
            .filter(Sale.sale_date.between(start_at, end_at))
            .one()
        )
        return SalesMetric(sales=sales, profit=profit, orders=orders)

    def _trend(self, start_date: date, end_date: date) -> list[dict]:
        start_at, end_at = self._bounds(start_date, end_date)
        day_expression = func.date(func.timezone(str(BUSINESS_TIMEZONE), Sale.sale_date))
        rows = (
            self.db.query(
                day_expression.label("day"),
                func.coalesce(func.sum(Sale.total_amount), 0),
                func.coalesce(func.sum(Sale.profit_amount), 0),
                func.count(Sale.id),
            )
            .filter(Sale.sale_date.between(start_at, end_at))
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

    def _ranking(self, kind: str, start_at: datetime, end_at: datetime) -> list[dict]:
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
            query.filter(Sale.sale_date.between(start_at, end_at))
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
            if not self.repo.get_by_invoice(candidate):
                return candidate
        raise conflict("Unable to generate invoice number")
