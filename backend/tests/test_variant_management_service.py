from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.product import ProductVariantUpdate
from app.services.variant_management_service import VariantManagementService


def test_variant_update_schema_accepts_pack_scan_configuration():
    payload = ProductVariantUpdate(barcode="PACK-6", internal_sku="PACK-6", scan_unit="PACK", pieces_per_pack=6)
    assert payload.scan_unit == "PACK"
    assert payload.pieces_per_pack == 6


def test_variant_update_schema_rejects_zero_pack_conversion():
    with pytest.raises(Exception):
        ProductVariantUpdate(scan_unit="PACK", pieces_per_pack=0)


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
