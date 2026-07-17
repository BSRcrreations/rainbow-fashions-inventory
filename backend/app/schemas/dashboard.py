from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas.purchase import PurchaseRead
from app.schemas.stock import StockHistoryRead


class TodaySaleItem(BaseModel):
    id: UUID
    product_id: UUID
    product_name: str
    size: str
    color: str
    qty: int
    before_stock: int
    after_stock: int
    reference: Optional[str]
    movement_date: datetime


class TodaySalesReport(BaseModel):
    total_count: int
    total_qty: int
    sales: list[TodaySaleItem]


class LowStockProduct(BaseModel):
    id: UUID
    name: str
    size: str
    color: str
    current_stock: int
    minimum_stock: int
    brand_name: str
    category_name: str


class DashboardSummary(BaseModel):
    total_products: int
    total_stock: int
    low_stock_count: int
    inventory_value: Decimal
    low_stock_products: list[LowStockProduct]
    recent_purchases: list[PurchaseRead]
    recent_stock_changes: list[StockHistoryRead]
    today_sales: Optional[TodaySalesReport] = None
