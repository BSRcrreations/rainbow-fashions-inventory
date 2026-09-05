from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.customer import CustomerCreate, CustomerRead
from app.schemas.sale import SaleCreate
from app.services.customer_phone import normalize_customer_phone
from app.services.sale_service import SaleService


def test_phone_normalization_uses_one_store_duplicate_key() -> None:
    assert normalize_customer_phone("+91 98765-43210") == "9876543210"
    assert normalize_customer_phone("0091 98765 43210") == "9876543210"
    assert CustomerCreate(name="Test Customer", phone="+91 98765-43210").phone == "9876543210"
    with pytest.raises(ValidationError):
        CustomerCreate(name="Test Customer", phone="123")


def test_customer_response_keeps_historical_one_character_names_listable() -> None:
    now = datetime(2026, 9, 5)
    customer = CustomerRead.model_validate(SimpleNamespace(id=uuid4(), store_id=uuid4(), name="a", created_at=now, updated_at=now))

    assert customer.name == "a"
    with pytest.raises(ValidationError):
        CustomerCreate(name="a")


def test_sale_payload_accepts_optional_customer_details_without_creating_on_input() -> None:
    payload = SaleCreate(payment_mode="CASH", customer_name="New Customer", customer_phone="9876543210", customer_details="Near the market", items=[{"product_variant_id": uuid4(), "quantity": 1}])
    assert payload.customer_phone == "9876543210"
    assert payload.customer_details == "Near the market"


def test_customer_is_created_only_inside_sale_transaction() -> None:
    store_id = uuid4()
    db = MagicMock()
    phone_query = db.query.return_value.filter.return_value.with_for_update.return_value
    phone_query.first.return_value = None
    phone_query.all.return_value = []
    service = SaleService.__new__(SaleService)
    service.db = db

    customer = service._customer_for_sale(None, "New Customer", "+91 98765-43210", "Address note", "CASH", store_id, datetime(2026, 9, 4))

    assert customer is not None
    assert customer.phone == "9876543210"
    assert customer.notes == "Address note"
    assert customer.last_purchase_at == datetime(2026, 9, 4)
    db.add.assert_called_once_with(customer)
    db.commit.assert_not_called()


def test_existing_customer_is_reused_for_same_normalized_phone() -> None:
    store_id = uuid4()
    existing = SimpleNamespace(id=uuid4(), store_id=store_id, phone="9876543210", is_active=True, last_purchase_at=None)
    db = MagicMock()
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = existing
    service = SaleService.__new__(SaleService)
    service.db = db

    customer = service._customer_for_sale(None, "Different typed name", "+91 98765-43210", None, "CASH", store_id, None)

    assert customer is existing
    db.add.assert_not_called()
