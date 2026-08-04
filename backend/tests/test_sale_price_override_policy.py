from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.enums import UserRole
from app.services.sale_service import SaleService


def _user(role: UserRole):
    return SimpleNamespace(id=uuid4(), role=role)


def _resolve(role: UserRole, submitted: Decimal | None, *, mrp: Decimal | None = Decimal("120")):
    return SaleService._resolve_unit_price(Decimal("100"), submitted, mrp, _user(role), uuid4(), "request-test")


def test_staff_can_sell_at_configured_price_but_cannot_override():
    assert _resolve(UserRole.STAFF, Decimal("100"))[0] == Decimal("100")
    for submitted in (Decimal("99"), Decimal("101")):
        with pytest.raises(HTTPException) as error:
            _resolve(UserRole.STAFF, submitted)
        assert error.value.status_code == 403
        assert error.value.detail["code"] == "selling_price_override_forbidden"


def test_manager_override_is_limited_by_mrp_and_audited():
    price, audit = _resolve(UserRole.MANAGER, Decimal("110"))
    assert price == Decimal("110")
    assert audit and audit["user_role"] == UserRole.MANAGER.value
    with pytest.raises(HTTPException) as error:
        _resolve(UserRole.MANAGER, Decimal("121"))
    assert error.value.status_code == 422
    assert error.value.detail["code"] == "selling_price_override_exceeds_mrp"


def test_owner_override_is_allowed_and_negative_prices_fail_for_every_role():
    price, audit = _resolve(UserRole.OWNER, Decimal("150"), mrp=Decimal("120"))
    assert price == Decimal("150")
    assert audit and audit["user_role"] == UserRole.OWNER.value
    for role in UserRole:
        with pytest.raises(HTTPException) as error:
            _resolve(role, Decimal("-1"))
        assert error.value.status_code == 422
        assert error.value.detail["code"] == "invalid_selling_price"


def test_policy_is_shared_by_variant_and_legacy_paths_before_mutation():
    staff = _user(UserRole.STAFF)
    with pytest.raises(HTTPException):
        SaleService._resolve_unit_price(Decimal("100"), Decimal("90"), Decimal("120"), staff, uuid4(), "request-test")
    # Both creation paths call this method before any sale, item, stock-history,
    # or audit object is added to the session.
