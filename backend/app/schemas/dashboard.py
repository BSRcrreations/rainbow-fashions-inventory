from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas.product import ProductRead
from app.schemas.purchase import PurchaseRead
from app.schemas.stock import StockHistoryRead


class LowStockProduct(BaseModel):
    id: UUID
    name: str
    size: Optional[str] = None
    color: Optional[str] = None
    current_stock: int
    minimum_stock: int
    brand_name: str
    category_name: str


class DistributionItem(BaseModel):
    label: str
    value: int


class DashboardSummary(BaseModel):
    total_products: int
    total_stock: int
    low_stock_count: int
    inventory_value: Decimal
    low_stock_products: list[LowStockProduct]
    recent_purchases: list[PurchaseRead]
    recent_stock_changes: list[StockHistoryRead]
    latest_products: list[ProductRead]
    stock_distribution: list[DistributionItem]
    category_distribution: list[DistributionItem]
    brand_distribution: list[DistributionItem]
    top_selling_products: list[DistributionItem]
