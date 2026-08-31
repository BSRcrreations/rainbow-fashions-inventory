from types import SimpleNamespace
from uuid import uuid4

from app.services.inventory_reconciliation_service import InventoryReconciliationService


def product(variant_stock: int, product_stock: int, inventory_stock: int, lots: int):
    return SimpleNamespace(
        id=uuid4(), name="Generated product", current_stock=product_stock,
        variants=[SimpleNamespace(id=uuid4(), current_stock=variant_stock, cost_lots=[SimpleNamespace(remaining_quantity=lots)])],
        inventory_items=[SimpleNamespace(store_id=STORE_ID, current_stock=inventory_stock)],
    )


STORE_ID = uuid4()


def test_healthy_variant_stock_and_lot_totals() -> None:
    item = InventoryReconciliationService(None)._product_items(product(8, 8, 8, 8), STORE_ID)[0]
    assert item.category == "HEALTHY"
    assert not item.repair_eligible


def test_aggregate_mismatch_is_repair_eligible() -> None:
    item = InventoryReconciliationService(None)._product_items(product(8, 4, 8, 8), STORE_ID)[0]
    assert item.category == "PRODUCT_AGGREGATE_MISMATCH"
    assert item.repair_eligible


def test_cost_lot_shortage_blocks_repair() -> None:
    item = InventoryReconciliationService(None)._product_items(product(8, 8, 8, 3), STORE_ID)[0]
    assert item.category == "COST_LOT_SHORTAGE"
    assert not item.repair_eligible


def test_negative_variant_stock_is_critical() -> None:
    item = InventoryReconciliationService(None)._product_items(product(-1, -1, -1, 0), STORE_ID)[0]
    assert item.category == "NEGATIVE_STOCK"
    assert item.severity == "CRITICAL"


def test_zero_stock_product_without_variants_is_a_legacy_catalog_warning() -> None:
    record = SimpleNamespace(id=uuid4(), name="Catalog-only legacy", current_stock=0, variants=[], inventory_items=[])

    item = InventoryReconciliationService(None)._product_items(record, STORE_ID)[0]

    assert item.category == "LEGACY_CATALOG_ONLY"
    assert item.severity == "WARNING"
    assert not item.repair_eligible


def test_zero_stock_product_without_inventory_aggregate_is_a_legacy_warning() -> None:
    record = product(0, 0, 0, 0)
    record.inventory_items = []

    item = InventoryReconciliationService(None)._product_items(record, STORE_ID)[0]

    assert item.category == "LEGACY_STORE_INVENTORY_ABSENT"
    assert item.severity == "WARNING"
    assert not item.repair_eligible
