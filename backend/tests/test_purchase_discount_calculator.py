from __future__ import annotations

from decimal import Decimal

import pytest

from app.services.discount_calculator import (
    DiscountCalculationError,
    PurchaseInvoiceDiscountInput,
    PurchaseLineDiscountInput,
    allocate_invoice_discount,
    calculate_invoice_discount,
    calculate_purchase_line,
)
from app.schemas.purchase import PurchaseItemReview
from app.services.purchase_service import PurchaseService
from uuid import uuid4


def line(**overrides: object):
    values: dict[str, object] = {
        "chargeable_quantity": Decimal("12"),
        "free_quantity": Decimal("0"),
        "list_unit_price": Decimal("157"),
    }
    values.update(overrides)
    return calculate_purchase_line(PurchaseLineDiscountInput(**values))


def test_percentage_discount_calculates_in_decimal_currency() -> None:
    result = line(discount_type="PERCENTAGE", discount_percentage=Decimal("10"))

    assert result.gross_amount == Decimal("1884.00")
    assert result.item_discount_amount == Decimal("188.40")
    assert result.taxable_amount == Decimal("1695.60")


def test_fixed_per_unit_fixed_line_and_final_unit_price() -> None:
    assert line(discount_type="FIXED_PER_UNIT", discount_per_unit=Decimal("10")).item_discount_amount == Decimal("120.00")
    assert line(discount_type="FIXED_PER_LINE", discount_amount=Decimal("100")).item_discount_amount == Decimal("100.00")
    assert line(discount_type="FINAL_UNIT_PRICE", invoiced_unit_price=Decimal("145")).item_discount_amount == Decimal("144.00")


def test_free_quantity_increases_received_stock_but_not_subtotal() -> None:
    result = line(free_quantity=Decimal("1"), discount_type="FREE_QUANTITY")

    assert result.gross_amount == Decimal("1884.00")
    assert result.received_quantity == Decimal("13.0000")
    assert result.effective_unit_cost == Decimal("144.92")


@pytest.mark.parametrize(
    "payload",
    [
        {"discount_type": "PERCENTAGE", "discount_percentage": Decimal("101")},
        {"discount_type": "FIXED_PER_LINE", "discount_amount": Decimal("1884.01")},
        {"discount_type": "MANUAL", "discount_amount": Decimal("10")},
        {"discount_type": "FINAL_UNIT_PRICE", "invoiced_unit_price": Decimal("158")},
    ],
)
def test_invalid_line_discounts_are_rejected(payload: dict[str, object]) -> None:
    with pytest.raises(DiscountCalculationError):
        line(**payload)


def test_invoice_discount_allocation_uses_last_line_for_rounding_remainder() -> None:
    rows = [line(), line(chargeable_quantity=Decimal("3"), list_unit_price=Decimal("100"))]
    discount = calculate_invoice_discount(
        PurchaseInvoiceDiscountInput(discount_type="PERCENTAGE", discount_percentage=Decimal("10")),
        sum((row.taxable_amount for row in rows), Decimal("0")),
    )
    allocations = allocate_invoice_discount(discount, rows, "BY_ITEM_VALUE")

    assert discount == Decimal("218.40")
    assert allocations == [Decimal("188.40"), Decimal("30.00")]


def test_manual_invoice_discount_requires_reason_and_do_not_allocate_keeps_cost_rows_unchanged() -> None:
    with pytest.raises(DiscountCalculationError):
        calculate_invoice_discount(
            PurchaseInvoiceDiscountInput(discount_type="MANUAL_ADJUSTMENT", discount_amount=Decimal("10")),
            Decimal("100"),
        )

    assert allocate_invoice_discount(Decimal("10"), [line()], "DO_NOT_ALLOCATE") == [Decimal("0.00")]


def test_legacy_flat_discount_remains_a_fixed_line_discount() -> None:
    item = PurchaseItemReview(
        product_name="Legacy line",
        size="",
        color="",
        quantity=1,
        purchase_price=Decimal("100"),
        discount=Decimal("10"),
        line_total=Decimal("90"),
    )

    created = PurchaseService.__new__(PurchaseService)._create_purchase_item(uuid4(), item)

    assert created.discount_type == "FIXED_PER_LINE"
    assert created.discount_amount == Decimal("10")
