from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.stock_scan import BarcodeDeletionCheckRead
from app.services.barcode_deletion_service import BarcodeDeletionService


def owner():
    return SimpleNamespace(store_id=uuid4())


def test_permanent_barcode_delete_requires_explicit_confirmation():
    with pytest.raises(HTTPException) as error:
        BarcodeDeletionService(SimpleNamespace()).permanently_delete("8905072571989", "", owner())
    assert error.value.status_code == 422
    assert error.value.detail["code"] == "DELETE_CONFIRMATION_REQUIRED"


def test_barcode_with_active_assignment_is_not_hard_deleted():
    db = SimpleNamespace(rollback=lambda: None)
    subject = BarcodeDeletionService(db)
    subject._assessment = lambda *_args, **_kwargs: BarcodeDeletionCheckRead(
        barcode="8905072571989", active_assignments=1, historical_references=0,
        draft_references=0, audit_references=0, can_permanently_delete=False,
        reason="Remove the current barcode assignment before permanently deleting its registration records.",
    )

    with pytest.raises(HTTPException) as error:
        subject.permanently_delete("8905072571989", "DELETE BARCODE", owner())
    assert error.value.status_code == 409
    assert error.value.detail["code"] == "BARCODE_DELETE_BLOCKED"


def test_barcode_history_is_reported_as_a_delete_blocker():
    check = BarcodeDeletionCheckRead(
        barcode="8905072571989", active_assignments=0, historical_references=3,
        draft_references=0, audit_references=2, can_permanently_delete=False,
        reason="Historical sales, purchases, or confirmed stock records were found and will be preserved.",
    )
    assert check.can_permanently_delete is False
    assert check.historical_references == 3
