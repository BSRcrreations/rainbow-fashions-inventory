from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.services.discount_calculator import money


SALE_DISCOUNT_TYPES = {"PERCENTAGE", "FIXED_AMOUNT"}


@dataclass(frozen=True)
class SaleDiscountError(ValueError):
    code: str
    message: str


def calculate_sale_discount(subtotal: Decimal, discount_type: str, discount_value: Decimal) -> Decimal:
    """Calculate a checkout-level discount using Decimal currency rounding.

    The caller supplies the subtotal derived from currently locked product prices;
    a client-provided total is deliberately never used here.
    """
    subtotal = money(subtotal)
    if discount_type not in SALE_DISCOUNT_TYPES:
        raise SaleDiscountError("DISCOUNT_TYPE_INVALID", "Select percentage or fixed-amount discount.")
    if discount_type == "PERCENTAGE":
        if discount_value < Decimal("0") or discount_value > Decimal("100"):
            raise SaleDiscountError("DISCOUNT_PERCENTAGE_INVALID", "Discount percentage must be between 0 and 100.")
        return money(subtotal * discount_value / Decimal("100"))
    if discount_value < Decimal("0"):
        raise SaleDiscountError("DISCOUNT_AMOUNT_INVALID", "Discount amount cannot be negative.")
    if discount_value > subtotal:
        raise SaleDiscountError("DISCOUNT_AMOUNT_INVALID", "Discount amount cannot be greater than the subtotal.")
    return money(discount_value)
