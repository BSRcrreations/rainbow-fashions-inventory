from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.product import Product
from app.models.purchase import Purchase
from app.models.stock_history import StockHistory
from app.schemas.dashboard import DashboardSummary, LowStockProduct


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def summary(self) -> DashboardSummary:
        total_products = self.db.query(func.count(Product.id)).scalar() or 0
        total_stock = self.db.query(func.coalesce(func.sum(Product.current_stock), 0)).scalar() or 0
        inventory_value = self.db.query(func.coalesce(func.sum(Product.current_stock * Product.purchase_price), 0)).scalar() or Decimal("0")
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
        )
