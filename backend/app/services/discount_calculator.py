from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Literal


MONEY_QUANTUM = Decimal("0.01")
QUANTITY_QUANTUM = Decimal("0.0001")

PurchaseDiscountType = Literal[
    "NONE",
    "PERCENTAGE",
    "FIXED_PER_UNIT",
    "FIXED_PER_LINE",
    "FINAL_UNIT_PRICE",
    "QUANTITY_SLAB",
    "FREE_QUANTITY",
    "MANUAL",
]
InvoiceDiscountType = Literal[
    "NONE",
    "PERCENTAGE",
    "FIXED_AMOUNT",
    "TRADE_DISCOUNT",
    "CASH_DISCOUNT",
    "COUPON",
    "PROMOTIONAL",
    "MANUAL_ADJUSTMENT",
]
AllocationMethod = Literal["BY_ITEM_VALUE", "BY_TAXABLE_VALUE", "BY_QUANTITY", "EQUALLY", "MANUAL", "DO_NOT_ALLOCATE"]


class DiscountCalculationError(ValueError):
    pass


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def quantity(value: Decimal) -> Decimal:
    return value.quantize(QUANTITY_QUANTUM, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class PurchaseLineDiscountInput:
    chargeable_quantity: Decimal
    free_quantity: Decimal
    list_unit_price: Decimal
    discount_type: PurchaseDiscountType = "NONE"
    discount_percentage: Decimal = Decimal("0")
    discount_per_unit: Decimal = Decimal("0")
    discount_amount: Decimal = Decimal("0")
    invoiced_unit_price: Decimal | None = None
    tax_rate: Decimal = Decimal("0")
    manual_reason: str | None = None


@dataclass(frozen=True)
class PurchaseLineDiscountResult:
    chargeable_quantity: Decimal
    free_quantity: Decimal
    received_quantity: Decimal
    gross_amount: Decimal
    item_discount_amount: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    net_line_amount: Decimal
    net_unit_price: Decimal
    effective_unit_cost: Decimal


@dataclass(frozen=True)
class PurchaseInvoiceDiscountInput:
    discount_type: InvoiceDiscountType = "NONE"
    discount_percentage: Decimal = Decimal("0")
    discount_amount: Decimal = Decimal("0")
    allocation_method: AllocationMethod = "BY_ITEM_VALUE"
    manual_reason: str | None = None


def calculate_purchase_line(value: PurchaseLineDiscountInput) -> PurchaseLineDiscountResult:
    chargeable_quantity = quantity(value.chargeable_quantity)
    free_quantity = quantity(value.free_quantity)
    list_unit_price = money(value.list_unit_price)
    if chargeable_quantity < 0:
        raise DiscountCalculationError("Chargeable quantity cannot be negative.")
    if free_quantity < 0:
        raise DiscountCalculationError("Free quantity cannot be negative.")
    if list_unit_price < 0:
        raise DiscountCalculationError("List price cannot be negative.")
    if value.tax_rate < 0 or value.tax_rate > Decimal("100"):
        raise DiscountCalculationError("Tax percentage must be between 0% and 100%.")

    gross_amount = money(chargeable_quantity * list_unit_price)
    discount_amount = _item_discount_amount(value, chargeable_quantity, list_unit_price, gross_amount)
    if discount_amount < 0:
        raise DiscountCalculationError("Discount cannot be negative.")
    if discount_amount > gross_amount:
        raise DiscountCalculationError("Discount cannot exceed the item gross amount.")

    taxable_amount = money(gross_amount - discount_amount)
    tax_amount = money(taxable_amount * value.tax_rate / Decimal("100"))
    received_quantity = quantity(chargeable_quantity + free_quantity)
    net_line_amount = money(taxable_amount + tax_amount)
    net_unit_price = money(taxable_amount / chargeable_quantity) if chargeable_quantity else Decimal("0.00")
    effective_unit_cost = money(taxable_amount / received_quantity) if received_quantity else Decimal("0.00")
    return PurchaseLineDiscountResult(
        chargeable_quantity=chargeable_quantity,
        free_quantity=free_quantity,
        received_quantity=received_quantity,
        gross_amount=gross_amount,
        item_discount_amount=discount_amount,
        taxable_amount=taxable_amount,
        tax_amount=tax_amount,
        net_line_amount=net_line_amount,
        net_unit_price=net_unit_price,
        effective_unit_cost=effective_unit_cost,
    )


def calculate_invoice_discount(value: PurchaseInvoiceDiscountInput, eligible_amount: Decimal) -> Decimal:
    eligible_amount = money(eligible_amount)
    if eligible_amount < 0:
        raise DiscountCalculationError("Eligible invoice amount cannot be negative.")
    if value.discount_type == "NONE":
        return Decimal("0.00")
    if value.discount_type == "PERCENTAGE":
        if value.discount_percentage < 0 or value.discount_percentage > Decimal("100"):
            raise DiscountCalculationError("Discount percentage must be between 0% and 100%.")
        amount = money(eligible_amount * value.discount_percentage / Decimal("100"))
    else:
        amount = money(value.discount_amount)
    if value.discount_type == "MANUAL_ADJUSTMENT" and not (value.manual_reason or "").strip():
        raise DiscountCalculationError("Enter a reason for this manual discount.")
    if amount < 0:
        raise DiscountCalculationError("Discount cannot be negative.")
    if amount > eligible_amount:
        raise DiscountCalculationError("Invoice discount cannot exceed the eligible invoice amount.")
    return amount


def allocate_invoice_discount(
    total_discount: Decimal,
    rows: Iterable[PurchaseLineDiscountResult],
    method: AllocationMethod,
) -> list[Decimal]:
    values = list(rows)
    total_discount = money(total_discount)
    if not values or total_discount == 0 or method == "DO_NOT_ALLOCATE":
        return [Decimal("0.00") for _ in values]
    if method == "MANUAL":
        raise DiscountCalculationError("Manual invoice allocation requires explicit line allocations.")

    if method == "BY_QUANTITY":
        weights = [row.chargeable_quantity for row in values]
    elif method == "BY_TAXABLE_VALUE":
        weights = [row.taxable_amount for row in values]
    elif method == "EQUALLY":
        weights = [Decimal("1") for _ in values]
    else:
        weights = [row.gross_amount for row in values]
    weight_total = sum(weights, Decimal("0"))
    if weight_total <= 0:
        raise DiscountCalculationError("Invoice discount cannot be allocated because no eligible item value exists.")

    allocations: list[Decimal] = []
    remaining = total_discount
    for index, (row, weight) in enumerate(zip(values, weights)):
        amount = remaining if index == len(values) - 1 else money(total_discount * weight / weight_total)
        if amount > row.taxable_amount:
            raise DiscountCalculationError("Invoice discount cannot make an item taxable amount negative.")
        allocations.append(amount)
        remaining = money(remaining - amount)
    return allocations


def _item_discount_amount(
    value: PurchaseLineDiscountInput,
    chargeable_quantity: Decimal,
    list_unit_price: Decimal,
    gross_amount: Decimal,
) -> Decimal:
    if value.discount_type in {"NONE", "FREE_QUANTITY", "QUANTITY_SLAB"}:
        return Decimal("0.00")
    if value.discount_type == "PERCENTAGE":
        if value.discount_percentage < 0 or value.discount_percentage > Decimal("100"):
            raise DiscountCalculationError("Discount percentage must be between 0% and 100%.")
        return money(gross_amount * value.discount_percentage / Decimal("100"))
    if value.discount_type == "FIXED_PER_UNIT":
        return money(chargeable_quantity * value.discount_per_unit)
    if value.discount_type in {"FIXED_PER_LINE", "MANUAL"}:
        if value.discount_type == "MANUAL" and not (value.manual_reason or "").strip():
            raise DiscountCalculationError("Enter a reason for this manual discount.")
        return money(value.discount_amount)
    if value.discount_type == "FINAL_UNIT_PRICE":
        if value.invoiced_unit_price is None or value.invoiced_unit_price < 0:
            raise DiscountCalculationError("Enter a non-negative final unit price.")
        return money(chargeable_quantity * (list_unit_price - money(value.invoiced_unit_price)))
    raise DiscountCalculationError("Unsupported discount type.")
