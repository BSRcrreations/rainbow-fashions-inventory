from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.enums import PricingType
from app.schemas.product import ProductUpdate
from app.services.product_service import ProductService


def stocked_product(store_id=None):
    store_id = store_id or uuid4()
    product_id, variant_id = uuid4(), uuid4()
    variant = SimpleNamespace(
        id=variant_id,
        product_id=product_id,
        store_id=store_id,
        size="34",
        color="Assorted",
        style_code=None,
        barcode="8906000000001",
        internal_sku="SOFTA-34",
        identity_key="softa-34",
        current_stock=25,
        selling_price=Decimal("395"),
        mrp=Decimal("395"),
        sale_items=[SimpleNamespace(id=uuid4())],
        purchase_items=[SimpleNamespace(id=uuid4())],
        stock_movements=[SimpleNamespace(id=uuid4())],
    )
    return SimpleNamespace(
        id=product_id,
        store_id=store_id,
        name="Softa padded bra",
        category_id=uuid4(),
        subcategory_id=uuid4(),
        brand_id=uuid4(),
        pricing_type=PricingType.OWN_PRICE,
        mrp=Decimal("395"),
        current_stock=25,
        variants=[variant],
        stock_movements=[SimpleNamespace(id=uuid4())],
        sale_items=[SimpleNamespace(id=uuid4())],
        purchase_items=[SimpleNamespace(id=uuid4())],
        product_date=date(2026, 8, 3),
    )


def configured_service(product):
    db = MagicMock()
    service = ProductService(db)
    service.get = MagicMock(return_value=product)
    service._ensure_hierarchy = MagicMock()
    service._validate_unique_product = MagicMock()
    return service, db


def test_rename_stocked_product_preserves_product_variant_stock_and_history():
    product = stocked_product()
    variant = product.variants[0]
    original_variant_id = variant.id
    original_stock_history = list(product.stock_movements)
    original_sale_history = list(product.sale_items)
    original_purchase_history = list(product.purchase_items)
    service, db = configured_service(product)

    result = service.update(product.id, ProductUpdate(name="Soft padded bra"), product.store_id)

    assert result.id == product.id
    assert product.name == "Soft padded bra"
    assert product.current_stock == 25
    assert product.variants[0].id == original_variant_id
    assert product.variants[0].current_stock == 25
    assert product.stock_movements == original_stock_history
    assert product.sale_items == original_sale_history
    assert product.purchase_items == original_purchase_history
    db.commit.assert_called_once()


def test_direct_stock_mutation_is_rejected_without_changing_metadata_or_stock():
    product = stocked_product()
    service, db = configured_service(product)

    with pytest.raises(HTTPException) as error:
        service.update(product.id, ProductUpdate(name="Soft padded bra", current_stock=1), product.store_id)

    assert error.value.status_code == 400
    assert error.value.detail["code"] == "STOCK_FIELDS_READ_ONLY"
    assert product.name == "Softa padded bra"
    assert product.current_stock == 25
    db.commit.assert_not_called()


def test_cross_store_product_update_is_denied():
    product = stocked_product()
    service, db = configured_service(product)

    with pytest.raises(HTTPException) as error:
        service.update(product.id, ProductUpdate(name="Soft padded bra"), uuid4())

    assert error.value.status_code == 404
    assert product.name == "Softa padded bra"
    db.commit.assert_not_called()


def test_duplicate_product_has_a_structured_conflict_code():
    service = ProductService(MagicMock())
    service.repo.get_duplicate = MagicMock(return_value=stocked_product())

    with pytest.raises(HTTPException) as error:
        service._validate_unique_product(uuid4(), uuid4(), uuid4(), "Soft padded bra", store_id=uuid4())

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "PRODUCT_ALREADY_EXISTS"


def test_product_metadata_change_records_an_audit_without_changing_stock():
    product = stocked_product()
    service, db = configured_service(product)
    owner = SimpleNamespace(id=uuid4(), role=SimpleNamespace(value="OWNER"))

    service.update(product.id, ProductUpdate(name="Soft padded bra"), product.store_id, owner, "product-edit-request")

    audit = db.add.call_args.args[0]
    assert audit.product_id == product.id
    assert audit.store_id == product.store_id
    assert audit.request_id == "product-edit-request"
    assert audit.before_values == {"name": "Softa padded bra"}
    assert audit.after_values == {"name": "Soft padded bra"}
    assert product.current_stock == 25
