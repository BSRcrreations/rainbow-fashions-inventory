#!/usr/bin/env python3
"""Fail-closed removal of Owner-approved legacy barcode relationships.

This is intentionally not an import command.  It removes only mappings named
in a checksum-pinned migration conflict report after proving that their
currently-attached target keys are exactly the report's obsolete targets.  The
catalog migration command can then plan the package's own mappings normally.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import Session, joinedload

from app.models.product import Product
from app.models.product_barcode import ProductBarcode, ProductBarcodeVariantTarget
from app.models.product_variant import ProductVariant
from app.models.sale import Sale
from app.models.store import Store
from app.models.purchase import Purchase
from app.services.test_to_production_migration_service import (
    MigrationSafetyError,
    TestToProductionMigrationService,
    _normal,
    variant_key,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _database_name(url: str) -> str:
    return url.rsplit("/", 1)[-1].split("?", 1)[0]


def _mapping_target_keys(db: Session, store: Store) -> dict[str, set[str]]:
    products = (
        db.query(Product)
        .options(joinedload(Product.category), joinedload(Product.subcategory), joinedload(Product.brand), joinedload(Product.variants))
        .filter(Product.store_id == store.id)
        .all()
    )
    variants_by_id: dict[object, str] = {}
    for product in products:
        product_data = {
            "category": product.category.name,
            "subcategory": product.subcategory.name,
            "brand": product.brand.name,
            "name": product.name,
            "sku": product.sku,
        }
        for variant in product.variants:
            variants_by_id[variant.id] = variant_key(product_data, {"size": variant.size, "color": variant.color})
    mappings = db.query(ProductBarcode).filter(ProductBarcode.store_id == store.id).all()
    targets = db.query(ProductBarcodeVariantTarget).filter(ProductBarcodeVariantTarget.store_id == store.id).all()
    by_mapping: dict[object, set[object]] = defaultdict(set)
    for target in targets:
        by_mapping[target.product_barcode_id].add(target.product_variant_id)
    return {
        _normal(mapping.barcode): {
            variants_by_id[target_id]
            for target_id in by_mapping[mapping.id] | {mapping.product_variant_id}
            if target_id in variants_by_id
        }
        for mapping in mappings
    }


def resolve(args: argparse.Namespace) -> int:
    if _database_name(args.target_database_url) != args.expected_database:
        raise MigrationSafetyError("The connection URL does not name the explicitly expected database.")
    package = TestToProductionMigrationService.read_package(args.package_dir)
    if package["package_id"] != args.package_id or package["content_sha256"] != args.package_sha256:
        raise MigrationSafetyError("Package ID or checksum does not match the Owner-approved package.")
    if _sha256(args.conflict_report) != args.conflict_report_sha256:
        raise MigrationSafetyError("Conflict report checksum does not match the Owner-approved report.")
    payload = json.loads(args.conflict_report.read_text(encoding="utf-8"))
    approved = payload.get("conflicts")
    if not isinstance(approved, list) or len(approved) != args.expected_conflicts:
        raise MigrationSafetyError("Conflict report does not contain the expected number of conflicts.")
    if any(item.get("kind") != "barcode_relationship" or not item.get("key") for item in approved):
        raise MigrationSafetyError("Only barcode_relationship conflicts are eligible for this resolver.")
    if len({item["key"] for item in approved}) != len(approved):
        raise MigrationSafetyError("The approved report repeats a barcode.")

    engine = create_engine(args.target_database_url, pool_pre_ping=True)
    with Session(engine) as db:
        actual_db = db.execute(text("select current_database()")).scalar_one()
        if actual_db != args.expected_database:
            raise MigrationSafetyError("Connected database identity does not match the requested target.")
        store = db.query(Store).filter(func.lower(Store.code) == _normal(args.target_store_code)).one_or_none()
        if not store:
            raise MigrationSafetyError("Target store was not found.")
        stock = db.query(func.coalesce(func.sum(ProductVariant.current_stock), 0)).filter(ProductVariant.store_id == store.id).scalar()
        sales = db.query(func.count(Sale.id)).filter(Sale.store_id == store.id).scalar()
        purchases = db.query(func.count(Purchase.id)).filter(Purchase.store_id == store.id).scalar()
        if (stock, sales, purchases) != (0, 0, 0):
            raise MigrationSafetyError("Resolver requires zero stock, sales, and purchases in the target store.")
        actual_targets = _mapping_target_keys(db, store)
        expected_by_barcode = {_normal(item["key"]): set(item["actual"]) for item in approved}
        current = {barcode: actual_targets.get(barcode) for barcode in expected_by_barcode}
        if current != expected_by_barcode:
            raise MigrationSafetyError("Current barcode targets differ from the approved obsolete mappings; refusing change.")
        mappings = (
            db.query(ProductBarcode)
            .filter(ProductBarcode.store_id == store.id, ProductBarcode.barcode.in_([item["key"] for item in approved]))
            .all()
        )
        if len(mappings) != len(approved):
            raise MigrationSafetyError("The exact approved barcode mapping rows are not present.")
        mapping_ids = [item.id for item in mappings]
        target_rows = db.query(ProductBarcodeVariantTarget).filter(ProductBarcodeVariantTarget.product_barcode_id.in_(mapping_ids)).all()
        evidence = {
            "package_id": package["package_id"],
            "package_sha256": package["content_sha256"],
            "conflict_report_sha256": args.conflict_report_sha256,
            "target_database": actual_db,
            "target_store": store.code,
            "conflicts_before": len(approved),
            "legacy_mapping_rows_removed": len(mappings),
            "legacy_target_rows_removed": len(target_rows),
            "stock_before": int(stock),
            "sales_before": int(sales),
            "purchases_before": int(purchases),
            "barcodes": sorted(item.barcode for item in mappings),
        }
        for item in target_rows:
            db.delete(item)
        db.flush()
        for item in mappings:
            db.delete(item)
        db.commit()
        args.evidence_output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove only checksum-approved obsolete production barcode mappings.")
    parser.add_argument("--package-dir", type=Path, required=True)
    parser.add_argument("--package-id", required=True)
    parser.add_argument("--package-sha256", required=True)
    parser.add_argument("--conflict-report", type=Path, required=True)
    parser.add_argument("--conflict-report-sha256", required=True)
    parser.add_argument("--expected-conflicts", type=int, required=True)
    parser.add_argument("--target-database-url", required=True)
    parser.add_argument("--expected-database", required=True)
    parser.add_argument("--target-store-code", required=True)
    parser.add_argument("--evidence-output", type=Path, required=True)
    args = parser.parse_args()
    try:
        return resolve(args)
    except MigrationSafetyError as exc:
        print(f"resolution safety check failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
