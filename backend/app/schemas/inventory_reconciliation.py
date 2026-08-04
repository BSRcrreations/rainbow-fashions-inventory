from __future__ import annotations

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReconciliationItem(BaseModel):
    product_id: UUID
    variant_id: Optional[UUID] = None
    product_name: str
    variant_stock: int
    product_stock: int
    product_inventory_stock: Optional[int] = None
    remaining_cost_lot_quantity: int
    expected_product_stock: int
    difference: int
    severity: str
    category: str
    likely_cause: str
    repair_eligible: bool


class ReconciliationSummary(BaseModel):
    total_products: int
    healthy_products: int
    critical_mismatches: int
    repair_eligible_products: int
    categories: dict[str, int]


class ReconciliationRepairRequest(BaseModel):
    product_ids: list[UUID] = Field(min_length=1, max_length=1000)
    confirmation: str = Field(min_length=1, max_length=80)
    idempotency_key: str = Field(min_length=12, max_length=120)


class ReconciliationRepairPreview(BaseModel):
    items: list[ReconciliationItem]
    total_products: int
    backup_gate_passed: bool
    confirmation_phrase: str


class ReconciliationRepairResult(BaseModel):
    repaired_product_ids: list[UUID]
    already_completed: bool = False
