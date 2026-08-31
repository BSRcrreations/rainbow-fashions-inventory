from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.product import ProductVariantDetailsCreate, ProductVariantUpdate
from app.services.variant_management_service import VariantManagementService


def test_variant_update_schema_accepts_pack_scan_configuration():
    payload = ProductVariantUpdate(barcode="PACK-6", internal_sku="PACK-6", scan_unit="PACK", pieces_per_pack=6)
    assert payload.scan_unit == "PACK"
    assert payload.pieces_per_pack == 6


def test_variant_update_schema_rejects_zero_pack_conversion():
    with pytest.raises(Exception):
        ProductVariantUpdate(scan_unit="PACK", pieces_per_pack=0)


@pytest.mark.parametrize("size", ["32B", "34C", "Free Size", "Custom Size", "Brand 44-DD"])
def test_variant_update_accepts_flexible_and_custom_sizes(size):
    assert ProductVariantUpdate(size=size).size == size


def test_add_details_schema_requires_reviewed_product_identity_but_never_stock_quantity():
    payload = ProductVariantDetailsCreate(
        product_id=uuid4(), barcode="NEW-DETAILS-1", internal_sku="NEW-DETAILS-1",
        selling_price=549, purchase_cost=390, scan_unit="PACK", pieces_per_pack=6,
    )
    assert payload.product_id is not None
    assert payload.pieces_per_pack == 6
    assert "current_stock" not in payload.model_dump()


def test_add_details_schema_rejects_incomplete_new_product_and_invalid_pack():
    with pytest.raises(Exception):
        ProductVariantDetailsCreate(barcode="NEW", internal_sku="NEW", selling_price=1, purchase_cost=1)
    with pytest.raises(Exception):
        ProductVariantDetailsCreate(product_id=uuid4(), barcode="NEW", internal_sku="NEW", selling_price=1, purchase_cost=1, scan_unit="PACK", pieces_per_pack=1)


def test_variant_identity_is_scoped_to_the_variant_and_catalogue_attributes():
    variant = SimpleNamespace(product_id=uuid4(), id=uuid4(), size="L", color="Blue", style_code=None, mrp=500, selling_price=450)
    identity = VariantManagementService._identity(variant)
    assert identity.split("|")[1:4] == ["l", "blue", ""]
    assert str(variant.id) in identity


def test_variant_delete_requires_its_own_explicit_confirmation():
    service = VariantManagementService(SimpleNamespace())
    with pytest.raises(HTTPException) as error:
        service.permanently_delete(uuid4(), "DELETE", SimpleNamespace(), "request-1")
    assert error.value.status_code == 422
    assert error.value.detail["code"] == "DELETE_CONFIRMATION_REQUIRED"


def test_duplicate_variant_error_identifies_the_existing_exact_variant_without_merging():
    existing = SimpleNamespace(id=uuid4(), size="XL", color="Black", current_stock=7, is_active=True)

    error = VariantManagementService._duplicate_variant_error(existing)

    assert error.status_code == 409
    assert error.detail["code"] == "VARIANT_ALREADY_EXISTS"
    assert error.detail["message"] == "XL / Black already exists for this product."
    assert error.detail["existing_variant"] == {
        "id": str(existing.id), "size": "XL", "color": "Black", "current_stock": 7, "is_active": True,
    }
