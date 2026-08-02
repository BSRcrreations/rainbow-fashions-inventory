from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.services.sale_discount import SaleDiscountError, calculate_sale_discount
from app.services.sale_service import SaleService


@pytest.mark.parametrize(
    ("discount_type", "value", "expected"),
    [
        ("PERCENTAGE", Decimal("0"), Decimal("0.00")),
        ("PERCENTAGE", Decimal("10"), Decimal("99.80")),
        ("PERCENTAGE", Decimal("7.5"), Decimal("74.85")),
        ("PERCENTAGE", Decimal("100"), Decimal("998.00")),
        ("FIXED_AMOUNT", Decimal("50"), Decimal("50.00")),
    ],
)
def test_calculates_checkout_discount_with_decimal_currency(discount_type: str, value: Decimal, expected: Decimal) -> None:
    assert calculate_sale_discount(Decimal("998.00"), discount_type, value) == expected


@pytest.mark.parametrize(
    ("discount_type", "value", "code", "message"),
    [
        ("PERCENTAGE", Decimal("100.01"), "DISCOUNT_PERCENTAGE_INVALID", "Discount percentage must be between 0 and 100."),
        ("PERCENTAGE", Decimal("-1"), "DISCOUNT_PERCENTAGE_INVALID", "Discount percentage must be between 0 and 100."),
        ("FIXED_AMOUNT", Decimal("998.01"), "DISCOUNT_AMOUNT_INVALID", "Discount amount cannot be greater than the subtotal."),
        ("FIXED_AMOUNT", Decimal("-1"), "DISCOUNT_AMOUNT_INVALID", "Discount amount cannot be negative."),
        ("UNKNOWN", Decimal("0"), "DISCOUNT_TYPE_INVALID", "Select percentage or fixed-amount discount."),
    ],
)
def test_rejects_invalid_checkout_discount(discount_type: str, value: Decimal, code: str, message: str) -> None:
    with pytest.raises(SaleDiscountError) as error:
        calculate_sale_discount(Decimal("998.00"), discount_type, value)

    assert error.value.code == code
    assert error.value.message == message


def test_rounds_half_up_to_currency_precision() -> None:
    assert calculate_sale_discount(Decimal("99.99"), "PERCENTAGE", Decimal("7.5")) == Decimal("7.50")


def test_service_returns_structured_discount_error_with_request_id() -> None:
    with pytest.raises(HTTPException) as error:
        SaleService._checkout_discount(Decimal("998.00"), "PERCENTAGE", Decimal("101"), "request-123")

    assert error.value.status_code == 400
    assert error.value.detail == {
        "message": "Discount percentage must be between 0 and 100.",
        "code": "DISCOUNT_PERCENTAGE_INVALID",
        "request_id": "request-123",
    }
