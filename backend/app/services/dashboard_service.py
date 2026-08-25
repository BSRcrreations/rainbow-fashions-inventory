from __future__ import annotations

from datetime import datetime, time, timezone
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.brand import Brand
from app.models.category import Category
from app.models.enums import StockMovementType, UserRole
from app.models.product import Product
from app.models.purchase import Purchase
from app.models.stock_history import StockHistory
from app.models.user import User
from app.schemas.dashboard import DashboardSummary, LowStockProduct, TodaySaleItem, TodaySalesReport
from app.services.inventory_valuation_service import InventoryValuationService


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def summary(self, current_user: User | None = None) -> DashboardSummary:
        total_products = self.db.query(func.count(Product.id)).scalar() or 0
        total_stock = self.db.query(func.coalesce(func.sum(Product.current_stock), 0)).scalar() or 0
        inventory_value = (
            InventoryValuationService(self.db).current_value(current_user.store_id)
            if current_user and current_user.store_id
            else Decimal("0")
        )
        low_stock_products = (
            self.db.query(Product)
            .options(joinedload(Product.brand), joinedload(Product.category))
            .filter(Product.current_stock <= Product.minimum_stock)
            .order_by(Product.current_stock.asc())
            .limit(10)
            .all()
        )
        recent_purchases = (
            self.db.query(Purchase)
            .options(joinedload(Purchase.items))
            .order_by(Purchase.created_at.desc())
            .limit(5)
            .all()
        )
        recent_stock_changes = (
            self.db.query(StockHistory)
            .order_by(StockHistory.movement_date.desc())
            .limit(10)
            .all()
        )
        latest_products = (
            self.db.query(Product)
            .options(joinedload(Product.brand), joinedload(Product.category))
            .order_by(Product.created_at.desc())
            .limit(5)
            .all()
        )
        out_of_stock = self.db.query(func.count(Product.id)).filter(Product.current_stock == 0).scalar() or 0
        low_stock = (
            self.db.query(func.count(Product.id))
            .filter(Product.current_stock > 0, Product.current_stock <= Product.minimum_stock)
            .scalar()
            or 0
        )
        in_stock = self.db.query(func.count(Product.id)).filter(Product.current_stock > Product.minimum_stock).scalar() or 0
        category_distribution = (
            self.db.query(Category.name, func.count(Product.id))
            .join(Product, Product.category_id == Category.id)
            .group_by(Category.name)
            .order_by(func.count(Product.id).desc())
            .limit(8)
            .all()
        )
        brand_distribution = (
            self.db.query(Brand.name, func.count(Product.id))
            .join(Product, Product.brand_id == Brand.id)
            .group_by(Brand.name)
            .order_by(func.count(Product.id).desc())
            .limit(8)
            .all()
        )
        today_sales: TodaySalesReport | None = None
        if current_user is not None and current_user.role == UserRole.OWNER:
            now = datetime.now(timezone.utc)
            start_of_day = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
            end_of_day = datetime.combine(now.date(), time.max, tzinfo=timezone.utc)
            sale_movements = (
                self.db.query(StockHistory)
                .options(joinedload(StockHistory.product))
                .filter(
                    StockHistory.movement_type == StockMovementType.SALE,
                    StockHistory.movement_date >= start_of_day,
                    StockHistory.movement_date <= end_of_day,
                )
                .order_by(StockHistory.movement_date.desc())
                .all()
            )
            today_sales = TodaySalesReport(
                total_count=len(sale_movements),
                total_qty=sum(movement.qty for movement in sale_movements),
                sales=[
                    TodaySaleItem(
                        id=movement.id,
                        product_id=movement.product_id,
                        product_name=movement.product.name,
                        size=movement.product.size,
                        color=movement.product.color,
                        qty=movement.qty,
                        before_stock=movement.before_stock,
                        after_stock=movement.after_stock,
                        reference=movement.reference,
                        movement_date=movement.movement_date,
                    )
                    for movement in sale_movements
                ],
            )

        return DashboardSummary(
            total_products=total_products,
            total_stock=total_stock,
            low_stock_count=len(low_stock_products),
            inventory_value=inventory_value,
            low_stock_products=[
                LowStockProduct(
                    id=product.id,
                    name=product.name,
                    size=product.size,
                    color=product.color,
                    current_stock=product.current_stock,
                    minimum_stock=product.minimum_stock,
                    brand_name=product.brand.name,
                    category_name=product.category.name,
                )
                for product in low_stock_products
            ],
            recent_purchases=recent_purchases,
            recent_stock_changes=recent_stock_changes,
            latest_products=latest_products,
            stock_distribution=[
                {"label": "In stock", "value": in_stock},
                {"label": "Low stock", "value": low_stock},
                {"label": "Out of stock", "value": out_of_stock},
            ],
            category_distribution=[{"label": name, "value": count} for name, count in category_distribution],
            brand_distribution=[{"label": name, "value": count} for name, count in brand_distribution],
            top_selling_products=[],
            today_sales=today_sales,
        )
