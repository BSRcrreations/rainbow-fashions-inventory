import copy
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.test_to_production_migration_service import (
    CATALOG_AND_OPENING_STOCK,
    MigrationSafetyError,
    TestToProductionMigrationService,
    _sha256,
)


def _package() -> dict:
    package = {
        "schema_version": 1,
        "package_id": "TTP-disposable-test-package",
        "source": {"database": "rainbow_test_db", "store_code": "TEST", "git_sha": "a" * 40, "exported_at": "2026-08-24T00:00:00+00:00"},
        "mode": CATALOG_AND_OPENING_STOCK,
        "catalog": {
            "categories": [{"name": "Tops", "description": None, "is_active": True}],
            "brands": [{"category": "Tops", "name": "Rainbow", "description": None, "is_active": True}],
            "products": [
                {
                    "category": "Tops", "subcategory": "T-Shirts", "brand": "Rainbow", "name": "Unique Tee", "sku": "UNIQUE-TEE",
                    "description": None, "hsn_code": None, "gst_rate": None, "unit": "Each", "warehouse": None,
                    "pricing_type": "MRP", "mrp": "499.00", "selling_price": "399.00", "purchase_cost": "200.00", "is_active": True,
                    "variants": [
                        {"variant_key": "sku:unique-tee|m|blue", "size": "M", "color": "Blue", "style_code": None, "model_number": None, "manufacturer_sku": None, "internal_sku": "UNIQUE-TEE-M", "primary_barcode": "UNIQUE-001", "mrp": "499.00", "selling_price": "399.00", "purchase_cost": "200.00", "average_cost": "200.00", "is_active": True},
                    ],
                },
                {
                    "category": "Tops", "subcategory": "T-Shirts", "brand": "Rainbow", "name": "Shared Tee", "sku": "SHARED-TEE",
                    "description": None, "hsn_code": None, "gst_rate": None, "unit": "Each", "warehouse": None,
                    "pricing_type": "MRP", "mrp": "599.00", "selling_price": "449.00", "purchase_cost": "250.00", "is_active": True,
                    "variants": [
                        {"variant_key": "sku:shared-tee|m|red", "size": "M", "color": "Red", "style_code": None, "model_number": None, "manufacturer_sku": None, "internal_sku": "SHARED-TEE-M", "primary_barcode": "SHARED-M", "mrp": "599.00", "selling_price": "449.00", "purchase_cost": "250.00", "average_cost": "250.00", "is_active": True},
                        {"variant_key": "sku:shared-tee|l|red", "size": "L", "color": "Red", "style_code": None, "model_number": None, "manufacturer_sku": None, "internal_sku": "SHARED-TEE-L", "primary_barcode": "SHARED-L", "mrp": "599.00", "selling_price": "449.00", "purchase_cost": "250.00", "average_cost": "250.00", "is_active": True},
                    ],
                },
            ],
        },
        "barcode_mappings": [
            {"barcode": "UNIQUE-001", "barcode_type": "MANUFACTURER", "manufacturer_barcode": True, "package_quantity": 1, "scan_unit": "PIECE", "inventory_unit": "PIECE", "base_unit_conversion": 1, "sale_mode": "PIECE_ONLY", "mrp": "499.00", "default_selling_price": "399.00", "active": True, "target_variant_keys": ["sku:unique-tee|m|blue"]},
            {"barcode": "SHARED-SIZES", "barcode_type": "MANUFACTURER", "manufacturer_barcode": True, "package_quantity": 1, "scan_unit": "PIECE", "inventory_unit": "PIECE", "base_unit_conversion": 1, "sale_mode": "PIECE_ONLY", "mrp": None, "default_selling_price": None, "active": True, "target_variant_keys": ["sku:shared-tee|l|red", "sku:shared-tee|m|red"]},
            {"barcode": "SHARED-PRODUCTS", "barcode_type": "MANUFACTURER", "manufacturer_barcode": True, "package_quantity": 1, "scan_unit": "PIECE", "inventory_unit": "PIECE", "base_unit_conversion": 1, "sale_mode": "PIECE_ONLY", "mrp": None, "default_selling_price": None, "active": True, "target_variant_keys": ["sku:shared-tee|m|red", "sku:unique-tee|m|blue"]},
        ],
        "opening_stock": [
            {"variant_key": "sku:unique-tee|m|blue", "quantity": 3, "unit_cost": "200.00"},
            {"variant_key": "sku:shared-tee|m|red", "quantity": 4, "unit_cost": "250.00"},
            {"variant_key": "sku:shared-tee|l|red", "quantity": 5, "unit_cost": "250.00"},
        ],
    }
    package["counts"] = TestToProductionMigrationService._counts(package)
    package["content_sha256"] = _sha256({key: value for key, value in package.items() if key != "content_sha256"})
    return package


def test_disposable_package_preserves_unique_and_shared_barcodes_and_value(tmp_path) -> None:
    package = _package()
    TestToProductionMigrationService.validate_package(package)
    package_dir = TestToProductionMigrationService.write_package(package, tmp_path)
    retry = TestToProductionMigrationService.read_package(package_dir)
    assert retry["package_id"] == package["package_id"]  # package ID is the server-side idempotency key
    assert retry["counts"] == {"categories": 1, "brands": 1, "products": 2, "variants": 3, "barcode_mappings": 3, "total_physical_pieces": 12, "cost_valuation": "2850.00"}
    assert next(item for item in retry["barcode_mappings"] if item["barcode"] == "SHARED-SIZES")["target_variant_keys"] == ["sku:shared-tee|l|red", "sku:shared-tee|m|red"]
    assert Decimal(retry["counts"]["cost_valuation"]) == Decimal("2850.00")


def test_package_tampering_or_duplicate_variant_key_is_rejected() -> None:
    package = _package()
    changed = copy.deepcopy(package)
    changed["opening_stock"][0]["quantity"] = 30
    with pytest.raises(MigrationSafetyError, match="checksum"):
        TestToProductionMigrationService.validate_package(changed)
    duplicate = copy.deepcopy(package)
    duplicate["catalog"]["products"][1]["variants"][1]["variant_key"] = "sku:shared-tee|m|red"
    duplicate["counts"] = TestToProductionMigrationService._counts(duplicate)
    duplicate["content_sha256"] = _sha256({key: value for key, value in duplicate.items() if key != "content_sha256"})
    with pytest.raises(MigrationSafetyError, match="duplicate"):
        TestToProductionMigrationService.validate_package(duplicate)


def test_production_execution_guard_requires_identity_and_all_gates() -> None:
    gates = {"gate_2": "PASS", "gate_3": "PASS", "gate_4": "PASS", "production_smoke_test": "PASS", "production_stock_reset": "PASS"}
    TestToProductionMigrationService._assert_production_identity("inventory_db", "current", "current_postgres_data", gates)
    with pytest.raises(MigrationSafetyError, match="Gate 2"):
        TestToProductionMigrationService._assert_production_identity("inventory_db", "current", "current_postgres_data", {**gates, "gate_3": "FAIL"})
    with pytest.raises(MigrationSafetyError, match="identity"):
        TestToProductionMigrationService._assert_production_identity("rainbow_test_db", "current", "current_postgres_data", gates)


def test_migration_restores_package_product_cost_after_different_variant_opening_costs(monkeypatch) -> None:
    """Opening cost lots keep their exact costs; package catalog cost wins afterward."""
    package = _package()
    shared = package["catalog"]["products"][1]
    shared["purchase_cost"] = "250.00"
    shared["variants"][0]["purchase_cost"] = shared["variants"][0]["average_cost"] = "260.00"
    shared["variants"][1]["purchase_cost"] = shared["variants"][1]["average_cost"] = "315.00"
    package["opening_stock"] = [
        {"variant_key": "sku:unique-tee|m|blue", "quantity": 3, "unit_cost": "200.00"},
        {"variant_key": "sku:shared-tee|m|red", "quantity": 4, "unit_cost": "260.00"},
        {"variant_key": "sku:shared-tee|l|red", "quantity": 5, "unit_cost": "315.00"},
    ]
    package["counts"] = TestToProductionMigrationService._counts(package)
    package["content_sha256"] = _sha256({key: value for key, value in package.items() if key != "content_sha256"})

    def fake_product(source: dict) -> SimpleNamespace:
        return SimpleNamespace(
            store_id="store", category=SimpleNamespace(name=source["category"]),
            subcategory=SimpleNamespace(name=source["subcategory"]), brand=SimpleNamespace(name=source["brand"]),
            name=source["name"], sku=source["sku"], mrp=Decimal(source["mrp"]),
            selling_price=Decimal(source["selling_price"]), purchase_price=Decimal(source["purchase_cost"]),
        )

    unique_product, shared_product = (fake_product(source) for source in package["catalog"]["products"])
    products = [unique_product, shared_product]
    variants = {
        "sku:unique-tee|m|blue": SimpleNamespace(current_stock=0, last_purchase_cost=Decimal("200"), average_cost=Decimal("200")),
        "sku:shared-tee|m|red": SimpleNamespace(current_stock=0, last_purchase_cost=Decimal("260"), average_cost=Decimal("260")),
        "sku:shared-tee|l|red": SimpleNamespace(current_stock=0, last_purchase_cost=Decimal("315"), average_cost=Decimal("315")),
    }
    resolved = {
        "sku:unique-tee|m|blue": (unique_product, variants["sku:unique-tee|m|blue"]),
        "sku:shared-tee|m|red": (shared_product, variants["sku:shared-tee|m|red"]),
        "sku:shared-tee|l|red": (shared_product, variants["sku:shared-tee|l|red"]),
    }

    class Query:
        def options(self, *args):
            return self

        def filter(self, *args):
            return self

        def all(self):
            return products

    class Session:
        def query(self, *_args):
            return Query()

    lots: list[tuple[int, Decimal]] = []

    class Poster:
        def post_migration_opening_stock(self, *, product, variant, quantity, unit_cost, **_kwargs):
            # This models the intentional generic receipt behaviour: latest
            # product cost follows the final receipt, while each lot keeps its
            # exact unit cost.
            product.purchase_price = unit_cost
            variant.current_stock += quantity
            variant.last_purchase_cost = unit_cost
            variant.average_cost = unit_cost
            lots.append((quantity, unit_cost))
            return SimpleNamespace(), SimpleNamespace(qty=quantity)

    monkeypatch.setattr("app.services.test_to_production_migration_service.OpeningStockImportService", lambda _db: Poster())
    service = TestToProductionMigrationService(Session())
    movements = service._post_opening_stock(package, SimpleNamespace(id="store"), SimpleNamespace(), resolved)
    service._restore_package_product_pricing(package, SimpleNamespace(id="store"))

    assert sum(item.qty for item in movements) == 12
    assert sum(quantity for quantity, _ in lots) == 12
    assert sum(quantity * cost for quantity, cost in lots) == Decimal("3215")
    assert shared_product.purchase_price == Decimal("250.00")
    assert variants["sku:shared-tee|m|red"].last_purchase_cost == Decimal("260.00")
    assert variants["sku:shared-tee|l|red"].last_purchase_cost == Decimal("315.00")
