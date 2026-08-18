from types import SimpleNamespace
from uuid import uuid4

from app.schemas.stock_scan import BarcodeLookupAssignmentRead
from app.services.barcode_resolution_service import BarcodeResolutionService


def assignment(*, product_id=None, colour="Black", active=True):
    return BarcodeLookupAssignmentRead(
        barcode_id=uuid4(), product_id=product_id or uuid4(), variant_id=uuid4(), product_name="OE Plain",
        brand_name="OE", category_name="Intimacy", size="XL", color=colour, current_stock=0, active=active,
    )


def service():
    return BarcodeResolutionService(SimpleNamespace())


def test_active_mapping_is_resolved_consistently_as_unique():
    subject = service()
    mapping = SimpleNamespace(active=True)
    found = assignment()
    subject.db.query = lambda *_: SimpleNamespace(filter=lambda *_: SimpleNamespace(first=lambda: mapping))
    subject._mapping_assignments = lambda *_: [found]

    result = subject.lookup_for_store("8905072571989", uuid4())

    assert result.status == "UNIQUE"
    assert result.assignments[0].product_name == "OE Plain"


def test_shared_mapping_reports_all_sizes():
    subject = service()
    product_id = uuid4()
    mapping = SimpleNamespace(active=True)
    subject.db.query = lambda *_: SimpleNamespace(filter=lambda *_: SimpleNamespace(first=lambda: mapping))
    subject._mapping_assignments = lambda *_: [assignment(product_id=product_id), assignment(product_id=product_id)]

    assert subject.lookup_for_store("8905072571989", uuid4()).status == "SHARED"


def test_inactive_mapping_releases_the_barcode():
    subject = service()
    mapping = SimpleNamespace(active=False)
    subject.db.query = lambda *_: SimpleNamespace(filter=lambda *_: SimpleNamespace(first=lambda: mapping))

    result = subject.lookup_for_store("8905072571989", uuid4())

    assert result.status == "AVAILABLE"


def test_missing_mapping_with_inactive_legacy_variant_is_stale():
    subject = service()
    subject.db.query = lambda *_: SimpleNamespace(filter=lambda *_: SimpleNamespace(first=lambda: None))
    subject._legacy_assignments = lambda *_: [assignment(active=False)]

    assert subject.lookup_for_store("8905072571989", uuid4()).status == "STALE"


def test_unrelated_active_variants_are_a_conflict():
    subject = service()
    mapping = SimpleNamespace(active=True)
    subject.db.query = lambda *_: SimpleNamespace(filter=lambda *_: SimpleNamespace(first=lambda: mapping))
    subject._mapping_assignments = lambda *_: [assignment(product_id=uuid4()), assignment(product_id=uuid4())]

    assert subject.lookup_for_store("8905072571989", uuid4()).status == "CONFLICT"
