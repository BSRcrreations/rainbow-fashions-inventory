from pathlib import Path


def test_catalog_migration_only_adds_the_import_idempotency_structure() -> None:
    migration = (Path(__file__).resolve().parents[1] / "alembic/versions/20260824_0044_catalog_migration_imports.py").read_text(encoding="utf-8")
    assert 'op.create_table(\n        "catalog_migration_imports"' in migration
    assert "op.create_index" in migration
    assert "op.execute" not in migration
    assert "op.bulk_insert" not in migration
    for table in ("products", "product_variants", "product_barcodes", "product_barcode_variant_targets", "stock_history", "inventory_cost_lots"):
        assert f'"{table}"' not in migration
