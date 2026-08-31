from __future__ import annotations

"""Fail-closed TEST catalog promotion package support.

This module intentionally contains no connection strings, passwords, user
records, sales, purchases, stock history, cost-lot history, or Alembic state in
its package format.  A package is a snapshot of catalog facts plus an optional
owner-approved final stock quantity for each exact variant.
"""

import csv
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, joinedload

from app.models.brand import Brand
from app.models.catalog_migration_import import CatalogMigrationImport
from app.models.category import Category
from app.models.enums import PricingType, UserRole
from app.models.product import Product
from app.models.product_barcode import ProductBarcode, ProductBarcodeVariantTarget
from app.models.product_variant import ProductVariant
from app.models.stock_history import StockHistory
from app.models.store import Store
from app.models.subcategory import SubCategory
from app.models.user import User
from app.services.opening_stock_import_service import OpeningStockImportService


CATALOG_ONLY = "CATALOG_ONLY"
CATALOG_AND_OPENING_STOCK = "CATALOG_AND_OPENING_STOCK"
SUPPORTED_MODES = {CATALOG_ONLY, CATALOG_AND_OPENING_STOCK}
PACKAGE_VERSION = 1


class MigrationSafetyError(RuntimeError):
    """A reportable fail-closed package, target, or approval problem."""


def _normal(value: Any) -> str:
    return " ".join(str(value or "").strip().split()).casefold()


def _money(value: Any) -> str:
    return format(Decimal(value or 0).quantize(Decimal("0.01")), "f")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def product_key(item: dict[str, Any]) -> str:
    sku = _normal(item.get("sku"))
    if sku:
        return f"sku:{sku}"
    return "family:" + "|".join(_normal(item.get(field)) for field in ("category", "subcategory", "brand", "name"))


def product_family_key(item: dict[str, Any]) -> str:
    return "|".join(_normal(item.get(field)) for field in ("category", "subcategory", "brand", "name"))


def variant_key(product: dict[str, Any], item: dict[str, Any]) -> str:
    # The approved key deliberately excludes opaque primary keys and barcodes:
    # the business identity is product family/style plus exact size and colour.
    return "|".join((product_key(product), _normal(item.get("size")), _normal(item.get("color"))))


@dataclass
class MigrationReport:
    records_to_create: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    records_existing: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    exact_matches: list[str] = field(default_factory=list)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    barcode_mappings_to_add: int = 0
    barcode_targets_to_add: int = 0
    stock_quantities_to_post: dict[str, int] = field(default_factory=dict)
    total_pieces: int = 0
    total_valuation: Decimal = Decimal("0")
    already_imported: bool = False

    def conflict(self, kind: str, key: str, expected: Any, actual: Any) -> None:
        self.conflicts.append({"kind": kind, "key": key, "expected": expected, "actual": actual})

    def as_dict(self) -> dict[str, Any]:
        return {
            "records_to_create": dict(self.records_to_create),
            "records_already_existing": dict(self.records_existing),
            "exact_matches": self.exact_matches,
            "conflicts": self.conflicts,
            "barcode_mappings_to_add": self.barcode_mappings_to_add,
            "barcode_targets_to_add": self.barcode_targets_to_add,
            "stock_quantities_to_post": self.stock_quantities_to_post,
            "total_pieces": self.total_pieces,
            "total_valuation": _money(self.total_valuation),
            "already_imported": self.already_imported,
        }


class TestToProductionMigrationService:
    """Create, inspect, dry-run and (only with all guards) apply packages."""

    __test__ = False

    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def read_approved_stock(path: Path) -> dict[str, int]:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        if not rows or set(rows[0]) != {"variant_key", "quantity"}:
            raise MigrationSafetyError("Approved stock CSV must have exactly variant_key,quantity headers.")
        approved: dict[str, int] = {}
        for number, row in enumerate(rows, start=2):
            key = (row.get("variant_key") or "").strip()
            try:
                quantity = int((row.get("quantity") or "").strip())
            except ValueError as exc:
                raise MigrationSafetyError(f"Approved stock row {number} has an invalid quantity.") from exc
            if not key or quantity < 0 or key in approved:
                raise MigrationSafetyError(f"Approved stock row {number} is blank, negative, or duplicated.")
            approved[key] = quantity
        return approved

    def export_package(
        self,
        *,
        source_store_code: str,
        source_database: str,
        source_git_sha: str,
        mode: str = CATALOG_ONLY,
        approved_stock: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        if mode not in SUPPORTED_MODES:
            raise MigrationSafetyError(f"Unsupported migration mode: {mode}")
        if source_database != "rainbow_test_db":
            raise MigrationSafetyError("Export is permitted only from rainbow_test_db.")
        if len(source_git_sha) < 7 or any(char not in "0123456789abcdef" for char in source_git_sha.lower()):
            raise MigrationSafetyError("source_git_sha must be a Git SHA.")
        store = self.db.query(Store).filter(func.lower(Store.code) == _normal(source_store_code)).one_or_none()
        if not store:
            raise MigrationSafetyError("Source TEST store was not found.")
        products = (
            self.db.query(Product)
            .options(joinedload(Product.category), joinedload(Product.subcategory), joinedload(Product.brand), joinedload(Product.variants))
            .filter(Product.store_id == store.id)
            .order_by(Product.name, Product.id)
            .all()
        )
        catalog_products: list[dict[str, Any]] = []
        variant_keys_by_id: dict[UUID, str] = {}
        categories: dict[str, dict[str, Any]] = {}
        brands: dict[tuple[str, str], dict[str, Any]] = {}
        for product in products:
            item = {
                "category": product.category.name,
                "subcategory": product.subcategory.name,
                "brand": product.brand.name,
                "name": product.name,
                "sku": product.sku,
                "description": product.description,
                "hsn_code": product.hsn_code,
                "gst_rate": _money(product.gst_rate) if product.gst_rate is not None else None,
                "unit": product.unit,
                "warehouse": product.warehouse,
                "pricing_type": product.pricing_type.value,
                "mrp": _money(product.mrp) if product.mrp is not None else None,
                "selling_price": _money(product.selling_price),
                "purchase_cost": _money(product.purchase_price),
                "is_active": bool(product.is_active),
                "variants": [],
            }
            categories.setdefault(_normal(product.category.name), {"name": product.category.name, "description": product.category.description, "is_active": bool(product.category.is_active)})
            brands.setdefault((_normal(product.category.name), _normal(product.brand.name)), {"category": product.category.name, "name": product.brand.name, "description": product.brand.description, "is_active": bool(product.brand.is_active)})
            for variant in sorted(product.variants, key=lambda candidate: (_normal(candidate.size), _normal(candidate.color), str(candidate.id))):
                source_variant = {
                    "size": variant.size,
                    "color": variant.color,
                    "style_code": variant.style_code,
                    "model_number": variant.model_number,
                    "manufacturer_sku": variant.manufacturer_sku,
                    "internal_sku": variant.internal_sku,
                    "primary_barcode": variant.barcode,
                    "mrp": _money(variant.mrp) if variant.mrp is not None else None,
                    "selling_price": _money(variant.selling_price),
                    "purchase_cost": _money(variant.last_purchase_cost),
                    "average_cost": _money(variant.average_cost),
                    "is_active": bool(variant.is_active),
                }
                key = variant_key(item, source_variant)
                source_variant["variant_key"] = key
                variant_keys_by_id[variant.id] = key
                item["variants"].append(source_variant)
            catalog_products.append(item)
        all_variant_keys = {key for key in variant_keys_by_id.values()}
        if mode == CATALOG_AND_OPENING_STOCK:
            if approved_stock is None or set(approved_stock) != all_variant_keys:
                missing = sorted(all_variant_keys - set(approved_stock or {}))
                extra = sorted(set(approved_stock or {}) - all_variant_keys)
                raise MigrationSafetyError(f"Approved stock must cover every exact variant once (missing={len(missing)}, extra={len(extra)}).")
        mappings = self._export_barcode_mappings(store.id, variant_keys_by_id)
        stock = []
        for product in catalog_products:
            for variant in product["variants"]:
                quantity = approved_stock[variant["variant_key"]] if approved_stock is not None else 0
                if mode == CATALOG_AND_OPENING_STOCK:
                    stock.append({"variant_key": variant["variant_key"], "quantity": quantity, "unit_cost": variant["average_cost"]})
        payload = {
            "schema_version": PACKAGE_VERSION,
            "package_id": f"TTP-{uuid4()}",
            "source": {"database": source_database, "store_code": store.code, "git_sha": source_git_sha.lower(), "exported_at": datetime.now(timezone.utc).isoformat()},
            "mode": mode,
            "catalog": {"categories": sorted(categories.values(), key=lambda value: _normal(value["name"])), "brands": sorted(brands.values(), key=lambda value: (_normal(value["category"]), _normal(value["name"]))), "products": catalog_products},
            "barcode_mappings": mappings,
            "opening_stock": stock,
        }
        payload["counts"] = self._counts(payload)
        payload["content_sha256"] = _sha256({key: value for key, value in payload.items() if key != "content_sha256"})
        return payload

    def _export_barcode_mappings(self, store_id: UUID, variant_keys_by_id: dict[UUID, str]) -> list[dict[str, Any]]:
        mappings = self.db.query(ProductBarcode).filter(ProductBarcode.store_id == store_id).order_by(ProductBarcode.barcode, ProductBarcode.id).all()
        targets = self.db.query(ProductBarcodeVariantTarget).filter(ProductBarcodeVariantTarget.store_id == store_id).all()
        by_mapping: dict[UUID, set[UUID]] = defaultdict(set)
        for target in targets:
            by_mapping[target.product_barcode_id].add(target.product_variant_id)
        result: list[dict[str, Any]] = []
        for mapping in mappings:
            target_ids = by_mapping[mapping.id] | {mapping.product_variant_id}
            if not target_ids.issubset(variant_keys_by_id):
                raise MigrationSafetyError("A source barcode mapping has a target outside the selected TEST catalog.")
            result.append({
                "barcode": mapping.barcode,
                "barcode_type": mapping.barcode_type,
                "manufacturer_barcode": bool(mapping.manufacturer_barcode),
                "package_quantity": mapping.package_quantity,
                "scan_unit": mapping.scan_unit,
                "inventory_unit": mapping.inventory_unit,
                "base_unit_conversion": mapping.base_unit_conversion,
                "sale_mode": mapping.sale_mode,
                "mrp": _money(mapping.mrp) if mapping.mrp is not None else None,
                "default_selling_price": _money(mapping.default_selling_price) if mapping.default_selling_price is not None else None,
                "active": bool(mapping.active),
                "target_variant_keys": sorted(variant_keys_by_id[target] for target in target_ids),
            })
        return result

    @staticmethod
    def _counts(package: dict[str, Any]) -> dict[str, Any]:
        products = package["catalog"]["products"]
        variants = [variant for product in products for variant in product["variants"]]
        stock = package.get("opening_stock", [])
        return {
            "categories": len(package["catalog"]["categories"]), "brands": len(package["catalog"]["brands"]),
            "products": len(products), "variants": len(variants), "barcode_mappings": len(package["barcode_mappings"]),
            "total_physical_pieces": sum(int(item["quantity"]) for item in stock),
            "cost_valuation": _money(sum((Decimal(item["unit_cost"]) * int(item["quantity"]) for item in stock), Decimal("0"))),
        }

    @staticmethod
    def write_package(package: dict[str, Any], output_dir: Path) -> Path:
        TestToProductionMigrationService.validate_package(package)
        output_dir.mkdir(parents=True, exist_ok=True)
        package_dir = output_dir / package["package_id"]
        if package_dir.exists():
            raise MigrationSafetyError(f"Package directory already exists: {package_dir}")
        package_dir.mkdir(mode=0o700)
        catalog = {"catalog": package["catalog"], "barcode_mappings": package["barcode_mappings"], "opening_stock": package["opening_stock"]}
        manifest = {key: value for key, value in package.items() if key not in catalog}
        catalog_path, manifest_path = package_dir / "catalog.json", package_dir / "manifest.json"
        catalog_path.write_bytes(_canonical(catalog))
        manifest_path.write_bytes(_canonical(manifest))
        checksums = f"{hashlib.sha256(catalog_path.read_bytes()).hexdigest()}  catalog.json\n{hashlib.sha256(manifest_path.read_bytes()).hexdigest()}  manifest.json\n"
        (package_dir / "checksums.sha256").write_text(checksums, encoding="ascii")
        return package_dir

    @staticmethod
    def read_package(package_dir: Path) -> dict[str, Any]:
        try:
            manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
            catalog = json.loads((package_dir / "catalog.json").read_text(encoding="utf-8"))
            expected = (package_dir / "checksums.sha256").read_text(encoding="ascii").splitlines()
        except (OSError, json.JSONDecodeError) as exc:
            raise MigrationSafetyError("Package is incomplete or unreadable.") from exc
        actual = {"catalog.json": hashlib.sha256((package_dir / "catalog.json").read_bytes()).hexdigest(), "manifest.json": hashlib.sha256((package_dir / "manifest.json").read_bytes()).hexdigest()}
        declared = {line.split("  ", 1)[1]: line.split("  ", 1)[0] for line in expected if "  " in line}
        if actual != declared:
            raise MigrationSafetyError("Package checksum verification failed.")
        package = {**manifest, **catalog}
        TestToProductionMigrationService.validate_package(package)
        return package

    @staticmethod
    def validate_package(package: dict[str, Any]) -> None:
        if package.get("schema_version") != PACKAGE_VERSION or package.get("mode") not in SUPPORTED_MODES:
            raise MigrationSafetyError("Unsupported migration package format.")
        if package.get("source", {}).get("database") != "rainbow_test_db":
            raise MigrationSafetyError("Package source must be rainbow_test_db.")
        required = {"package_id", "source", "catalog", "barcode_mappings", "opening_stock", "counts", "content_sha256", "mode"}
        if not required.issubset(package):
            raise MigrationSafetyError("Package manifest is missing required data.")
        expected = _sha256({key: value for key, value in package.items() if key != "content_sha256"})
        if package["content_sha256"] != expected:
            raise MigrationSafetyError("Package content checksum verification failed.")
        if package["counts"] != TestToProductionMigrationService._counts(package):
            raise MigrationSafetyError("Package count/valuation verification failed.")
        if package["mode"] == CATALOG_ONLY and package["opening_stock"]:
            raise MigrationSafetyError("CATALOG_ONLY packages cannot carry opening stock.")
        variant_keys = [variant.get("variant_key") for product in package["catalog"]["products"] for variant in product.get("variants", [])]
        if not variant_keys or len(variant_keys) != len(set(variant_keys)) or any(not key for key in variant_keys):
            raise MigrationSafetyError("Package contains duplicate or blank exact variant business keys.")
        if package["mode"] == CATALOG_AND_OPENING_STOCK:
            stock_keys = [item.get("variant_key") for item in package["opening_stock"]]
            if len(stock_keys) != len(set(stock_keys)) or set(stock_keys) != set(variant_keys):
                raise MigrationSafetyError("Opening-stock entries must cover every exact variant exactly once.")
        if any(not set(mapping.get("target_variant_keys", [])) or not set(mapping["target_variant_keys"]).issubset(variant_keys) for mapping in package["barcode_mappings"]):
            raise MigrationSafetyError("A barcode mapping has no valid exact-variant target.")
        barcodes = [_normal(mapping.get("barcode")) for mapping in package["barcode_mappings"]]
        if any(not barcode for barcode in barcodes) or len(barcodes) != len(set(barcodes)):
            raise MigrationSafetyError("Package contains duplicate or blank barcode mappings.")

    def dry_run(self, package: dict[str, Any], *, target_store_code: str) -> MigrationReport:
        self.validate_package(package)
        store = self.db.query(Store).filter(func.lower(Store.code) == _normal(target_store_code)).one_or_none()
        if not store:
            raise MigrationSafetyError("Target production store was not found.")
        existing = self.db.query(CatalogMigrationImport).filter_by(store_id=store.id, package_id=package["package_id"]).first()
        report = self._plan(package, store)
        if existing and existing.status == "COMPLETED":
            report.already_imported = True
            report.exact_matches.append(f"package:{package['package_id']}")
        elif existing:
            report.conflict("package_status", package["package_id"], "not previously attempted", existing.status)
        return report

    def _plan(self, package: dict[str, Any], store: Store) -> MigrationReport:
        report = MigrationReport()
        products = self.db.query(Product).options(joinedload(Product.category), joinedload(Product.subcategory), joinedload(Product.brand), joinedload(Product.variants)).filter(Product.store_id == store.id).all()
        target_by_key: dict[str, list[Product]] = defaultdict(list)
        target_by_family: dict[str, list[Product]] = defaultdict(list)
        target_variants: dict[str, list[ProductVariant]] = defaultdict(list)
        target_variants_by_barcode: dict[str, list[ProductVariant]] = defaultdict(list)
        for product in products:
            product_data = {"category": product.category.name, "subcategory": product.subcategory.name, "brand": product.brand.name, "name": product.name, "sku": product.sku}
            target_by_key[product_key(product_data)].append(product)
            target_by_family[product_family_key(product_data)].append(product)
            for variant in product.variants:
                target_variants[variant_key(product_data, {"size": variant.size, "color": variant.color})].append(variant)
                target_variants_by_barcode[_normal(variant.barcode)].append(variant)
        target_categories = {_normal(category.name): category for category in self.db.query(Category).filter(Category.store_id == store.id).all()}
        target_brands = {(_normal(brand.category.name), _normal(brand.name)): brand for brand in self.db.query(Brand).options(joinedload(Brand.category)).filter(Brand.store_id == store.id).all()}
        for category in package["catalog"]["categories"]:
            key = _normal(category["name"])
            (report.records_existing if key in target_categories else report.records_to_create)["categories"] += 1
        for brand in package["catalog"]["brands"]:
            key = (_normal(brand["category"]), _normal(brand["name"]))
            (report.records_existing if key in target_brands else report.records_to_create)["brands"] += 1
        source_variant_keys: set[str] = set()
        for source_product in package["catalog"]["products"]:
            key, family = product_key(source_product), product_family_key(source_product)
            matches = target_by_key[key]
            if len(matches) > 1:
                report.conflict("product", key, "one exact production product", f"{len(matches)} products")
                continue
            if not matches and target_by_family[family] and source_product.get("sku"):
                report.conflict("product", family, f"SKU {source_product['sku']}", "production product family has a different SKU")
            (report.records_existing if matches else report.records_to_create)["products"] += 1
            if matches:
                report.exact_matches.append(f"product:{key}")
                actual_product_prices = (_money(matches[0].mrp) if matches[0].mrp is not None else None, _money(matches[0].selling_price), _money(matches[0].purchase_price))
                expected_product_prices = (source_product.get("mrp"), source_product["selling_price"], source_product["purchase_cost"])
                if expected_product_prices != actual_product_prices:
                    report.conflict("product_price", key, expected_product_prices, actual_product_prices)
            for source_variant in source_product["variants"]:
                vkey = source_variant["variant_key"]
                source_variant_keys.add(vkey)
                variants = target_variants[vkey]
                if len(variants) > 1:
                    report.conflict("variant", vkey, "one exact production variant", f"{len(variants)} variants")
                    continue
                (report.records_existing if variants else report.records_to_create)["variants"] += 1
                if variants:
                    actual = variants[0]
                    expected_prices = (source_variant.get("mrp"), source_variant["selling_price"], source_variant["purchase_cost"], source_variant["average_cost"])
                    actual_prices = (_money(actual.mrp) if actual.mrp is not None else None, _money(actual.selling_price), _money(actual.last_purchase_cost), _money(actual.average_cost))
                    if expected_prices != actual_prices:
                        report.conflict("price", vkey, expected_prices, actual_prices)
                    else:
                        report.exact_matches.append(f"variant:{vkey}")
                    if _normal(actual.barcode) != _normal(source_variant["primary_barcode"]):
                        report.conflict("variant_primary_barcode", vkey, source_variant["primary_barcode"], actual.barcode)
                elif target_variants_by_barcode[_normal(source_variant["primary_barcode"])]:
                    existing = target_variants_by_barcode[_normal(source_variant["primary_barcode"])]
                    report.conflict("variant_primary_barcode", vkey, "unassigned", [str(item.id) for item in existing])
        if source_variant_keys != {variant["variant_key"] for product in package["catalog"]["products"] for variant in product["variants"]}:
            report.conflict("package", package["package_id"], "unique source variant keys", "duplicate variant business keys")
        mapping_targets = self._target_mapping_targets(store.id, target_variants)
        target_mappings = {_normal(item.barcode): item for item in self.db.query(ProductBarcode).filter(ProductBarcode.store_id == store.id).all()}
        for mapping in package["barcode_mappings"]:
            barcode = _normal(mapping["barcode"])
            actual_targets = mapping_targets.get(barcode)
            expected_targets = set(mapping["target_variant_keys"])
            if actual_targets is None:
                report.barcode_mappings_to_add += 1
                report.barcode_targets_to_add += len(expected_targets)
            elif actual_targets != expected_targets:
                report.conflict("barcode_relationship", mapping["barcode"], sorted(expected_targets), sorted(actual_targets))
            else:
                report.records_existing["barcode_mappings"] += 1
                report.exact_matches.append(f"barcode:{mapping['barcode']}")
                actual_mapping = target_mappings[barcode]
                expected_values = (mapping["barcode_type"], mapping["manufacturer_barcode"], mapping["package_quantity"], mapping["scan_unit"], mapping["inventory_unit"], mapping["base_unit_conversion"], mapping["sale_mode"], mapping.get("mrp"), mapping.get("default_selling_price"), mapping["active"])
                actual_values = (actual_mapping.barcode_type, actual_mapping.manufacturer_barcode, actual_mapping.package_quantity, actual_mapping.scan_unit, actual_mapping.inventory_unit, actual_mapping.base_unit_conversion, actual_mapping.sale_mode, _money(actual_mapping.mrp) if actual_mapping.mrp is not None else None, _money(actual_mapping.default_selling_price) if actual_mapping.default_selling_price is not None else None, actual_mapping.active)
                if expected_values != actual_values:
                    report.conflict("barcode_mapping", mapping["barcode"], expected_values, actual_values)
        if package["mode"] == CATALOG_AND_OPENING_STOCK:
            for stock in package["opening_stock"]:
                quantity = int(stock["quantity"])
                report.stock_quantities_to_post[stock["variant_key"]] = quantity
                report.total_pieces += quantity
                report.total_valuation += Decimal(stock["unit_cost"]) * quantity
        return report

    def _target_mapping_targets(self, store_id: UUID, target_variants: dict[str, list[ProductVariant]]) -> dict[str, set[str]]:
        variant_key_by_id: dict[UUID, str] = {variant.id: key for key, variants in target_variants.items() for variant in variants}
        mappings = self.db.query(ProductBarcode).filter(ProductBarcode.store_id == store_id).all()
        targets = self.db.query(ProductBarcodeVariantTarget).filter(ProductBarcodeVariantTarget.store_id == store_id).all()
        by_mapping: dict[UUID, set[UUID]] = defaultdict(set)
        for target in targets:
            by_mapping[target.product_barcode_id].add(target.product_variant_id)
        return {_normal(mapping.barcode): {variant_key_by_id[variant_id] for variant_id in by_mapping[mapping.id] | {mapping.product_variant_id} if variant_id in variant_key_by_id} for mapping in mappings}

    def execute(
        self,
        package: dict[str, Any],
        *,
        target_store_code: str,
        executing_user_id: UUID,
        owner_authorization: str | None,
        target_database: str,
        compose_project: str,
        postgres_volume: str,
        gate_evidence: dict[str, Any],
    ) -> MigrationReport:
        self.validate_package(package)
        self._assert_production_identity(target_database, compose_project, postgres_volume, gate_evidence)
        try:
            with self.db.begin():
                store = self.db.query(Store).filter(func.lower(Store.code) == _normal(target_store_code)).one_or_none()
                if not store:
                    raise MigrationSafetyError("Target production store was not found.")
                user = self.db.query(User).filter(User.id == executing_user_id, User.store_id == store.id, User.is_active.is_(True)).one_or_none()
                if not user:
                    raise MigrationSafetyError("An active executing user in the target store is required.")
                existing = self.db.query(CatalogMigrationImport).filter_by(store_id=store.id, package_id=package["package_id"]).with_for_update().first()
                if existing and existing.status == "COMPLETED":
                    report = self._plan(package, store)
                    if report.conflicts:
                        raise MigrationSafetyError("Completed package no longer matches the target catalog; reconcile before retrying.")
                    report.already_imported = True
                    return report
                if existing:
                    raise MigrationSafetyError(f"Package is already in {existing.status}; inspect before retrying.")
                if package["mode"] == CATALOG_AND_OPENING_STOCK:
                    if user.role != UserRole.OWNER:
                        raise MigrationSafetyError("Opening stock requires an active Owner user.")
                    expected_authorization = f"OWNER APPROVED OPENING STOCK {package['package_id']}"
                    if owner_authorization != expected_authorization:
                        raise MigrationSafetyError(f"Explicit owner authorization must be exactly: {expected_authorization}")
                    if self.db.query(func.coalesce(func.sum(ProductVariant.current_stock), 0)).filter(ProductVariant.store_id == store.id).scalar() != 0:
                        raise MigrationSafetyError("Production stock is not zero; opening stock cannot be posted.")
                report = self._plan(package, store)
                if report.conflicts:
                    raise MigrationSafetyError("Conflicts were found; no production records were changed.")
                record = CatalogMigrationImport(store_id=store.id, package_id=package["package_id"], package_sha256=package["content_sha256"], mode=package["mode"], status="POSTING", source_database=package["source"]["database"], source_git_sha=package["source"]["git_sha"], executed_by=user.id, manifest_json={key: value for key, value in package.items() if key not in {"catalog", "barcode_mappings", "opening_stock"}})
                self.db.add(record)
                self.db.flush()
                resolved = self._create_catalog(package, store, user)
                self._create_barcode_mappings(package, store, user, resolved)
                movements = self._post_opening_stock(package, store, user, resolved)
                # Opening-stock posting deliberately updates a product's latest
                # receipt cost.  A TEST catalog package, however, is an
                # authoritative catalog snapshot, so restore its product-level
                # pricing after the cost lots and exact variant costs exist.
                self._restore_package_product_pricing(package, store)
                self.db.flush()
                self._verify_post_import(package, store, movements)
                record.status = "COMPLETED"
                record.completed_at = datetime.now(timezone.utc)
                record.summary_json = {**report.as_dict(), "opening_stock_movement_ids": [str(item.id) for item in movements]}
            return report
        except Exception:
            self.db.rollback()
            raise

    def reconcile_completed_catalog(
        self,
        package: dict[str, Any],
        *,
        target_store_code: str,
        executing_user_id: UUID,
        owner_authorization: str | None,
        target_database: str,
        compose_project: str,
        postgres_volume: str,
        gate_evidence: dict[str, Any],
    ) -> dict[str, Any]:
        """Restore package-defined product pricing for an already-completed import.

        This is deliberately narrower than ``execute``: it never creates
        catalog records, barcodes, stock movements, or cost lots.  It is only
        eligible when the same checksum-pinned package is already COMPLETED.
        """
        self.validate_package(package)
        self._assert_production_identity(target_database, compose_project, postgres_volume, gate_evidence)
        try:
            with self.db.begin():
                store = self.db.query(Store).filter(func.lower(Store.code) == _normal(target_store_code)).one_or_none()
                if not store:
                    raise MigrationSafetyError("Target production store was not found.")
                user = self.db.query(User).filter(User.id == executing_user_id, User.store_id == store.id, User.is_active.is_(True)).one_or_none()
                if not user or user.role != UserRole.OWNER:
                    raise MigrationSafetyError("An active Owner in the target store is required.")
                expected_authorization = f"OWNER APPROVED CATALOG RECONCILIATION {package['package_id']}"
                if owner_authorization != expected_authorization:
                    raise MigrationSafetyError(f"Explicit owner authorization must be exactly: {expected_authorization}")
                record = self.db.query(CatalogMigrationImport).filter_by(store_id=store.id, package_id=package["package_id"]).with_for_update().one_or_none()
                if not record or record.status != "COMPLETED" or record.package_sha256 != package["content_sha256"]:
                    raise MigrationSafetyError("Only the matching completed package may be reconciled.")
                changed = self._restore_package_product_pricing(package, store, completed_import_repair=True)
                self.db.flush()
                verification = self._plan(package, store)
                if verification.conflicts:
                    raise MigrationSafetyError("Catalog reconciliation left package conflicts; transaction will roll back.")
                record.summary_json = {
                    **(record.summary_json or {}),
                    "catalog_reconciliation": {
                        "reconciled_at": datetime.now(timezone.utc).isoformat(),
                        "product_purchase_price_repairs": changed,
                    },
                }
            return {"package_id": package["package_id"], "product_purchase_price_repairs": changed}
        except Exception:
            self.db.rollback()
            raise

    @staticmethod
    def _assert_production_identity(target_database: str, compose_project: str, postgres_volume: str, gates: dict[str, Any]) -> None:
        if target_database != "inventory_db" or compose_project != "current" or postgres_volume != "current_postgres_data":
            raise MigrationSafetyError("Production identity must be inventory_db / current / current_postgres_data.")
        required = {"gate_2": "PASS", "gate_3": "PASS", "gate_4": "PASS", "production_smoke_test": "PASS", "production_stock_reset": "PASS"}
        if {key: gates.get(key) for key in required} != required:
            raise MigrationSafetyError("Gate 2, Gate 3, Gate 4, production smoke test, and zero-stock reset evidence must all be PASS.")

    def _create_catalog(self, package: dict[str, Any], store: Store, user: User) -> dict[str, tuple[Product, ProductVariant]]:
        categories = {_normal(item.name): item for item in self.db.query(Category).filter(Category.store_id == store.id).all()}
        for source in package["catalog"]["categories"]:
            categories.setdefault(_normal(source["name"]), Category(store_id=store.id, name=source["name"], description=source.get("description"), is_active=source.get("is_active", True)))
            self.db.add(categories[_normal(source["name"])])
        self.db.flush()
        subcategories = {(_normal(item.category.name), _normal(item.name)): item for item in self.db.query(SubCategory).options(joinedload(SubCategory.category)).filter(SubCategory.store_id == store.id).all()}
        brands = {(_normal(item.category.name), _normal(item.name)): item for item in self.db.query(Brand).options(joinedload(Brand.category)).filter(Brand.store_id == store.id).all()}
        resolved: dict[str, tuple[Product, ProductVariant]] = {}
        existing = self.db.query(Product).options(joinedload(Product.category), joinedload(Product.subcategory), joinedload(Product.brand), joinedload(Product.variants)).filter(Product.store_id == store.id).all()
        product_by_key = {product_key({"category": item.category.name, "subcategory": item.subcategory.name, "brand": item.brand.name, "name": item.name, "sku": item.sku}): item for item in existing}
        for source in package["catalog"]["products"]:
            category = categories[_normal(source["category"])]
            sub_key, brand_key = (_normal(source["category"]), _normal(source["subcategory"])), (_normal(source["category"]), _normal(source["brand"]))
            if sub_key not in subcategories:
                subcategories[sub_key] = SubCategory(store_id=store.id, category_id=category.id, name=source["subcategory"])
                self.db.add(subcategories[sub_key]); self.db.flush()
            if brand_key not in brands:
                brands[brand_key] = Brand(store_id=store.id, category_id=category.id, name=source["brand"])
                self.db.add(brands[brand_key]); self.db.flush()
            key = product_key(source)
            product = product_by_key.get(key)
            if not product:
                product = Product(store_id=store.id, category_id=category.id, subcategory_id=subcategories[sub_key].id, brand_id=brands[brand_key].id, sku=source.get("sku") or None, name=source["name"], purchase_price=Decimal(source["purchase_cost"]), selling_price=Decimal(source["selling_price"]), pricing_type=PricingType(source["pricing_type"]), mrp=Decimal(source["mrp"]) if source.get("mrp") else None, hsn_code=source.get("hsn_code"), gst_rate=Decimal(source["gst_rate"]) if source.get("gst_rate") else None, description=source.get("description"), unit=source.get("unit") or "Each", warehouse=source.get("warehouse"), is_active=source.get("is_active", True))
                self.db.add(product); self.db.flush(); product_by_key[key] = product
            variants_by_key = {variant_key(source, {"size": item.size, "color": item.color}): item for item in product.variants}
            for source_variant in source["variants"]:
                vkey = source_variant["variant_key"]
                variant = variants_by_key.get(vkey)
                if not variant:
                    internal_sku = source_variant.get("internal_sku") or f"MIG-{hashlib.sha256(vkey.encode()).hexdigest()[:20]}"
                    variant = ProductVariant(store_id=store.id, product_id=product.id, size=source_variant.get("size"), color=source_variant.get("color"), style_code=source_variant.get("style_code"), model_number=source_variant.get("model_number"), manufacturer_sku=source_variant.get("manufacturer_sku"), internal_sku=internal_sku, barcode=source_variant["primary_barcode"], identity_key=f"migration|{product.id}|{_normal(source_variant.get('size'))}|{_normal(source_variant.get('color'))}", mrp=Decimal(source_variant["mrp"]) if source_variant.get("mrp") else None, selling_price=Decimal(source_variant["selling_price"]), last_purchase_cost=Decimal(source_variant["purchase_cost"]), average_cost=Decimal(source_variant["average_cost"]), current_stock=0, is_active=source_variant.get("is_active", True))
                    self.db.add(variant); self.db.flush(); variants_by_key[vkey] = variant
                resolved[vkey] = (product, variant)
        return resolved

    def _create_barcode_mappings(self, package: dict[str, Any], store: Store, user: User, resolved: dict[str, tuple[Product, ProductVariant]]) -> None:
        existing = {_normal(item.barcode): item for item in self.db.query(ProductBarcode).filter(ProductBarcode.store_id == store.id).all()}
        for source in package["barcode_mappings"]:
            barcode = _normal(source["barcode"])
            if barcode in existing:
                continue
            targets = [resolved[key] for key in source["target_variant_keys"]]
            product, primary = targets[0]
            mapping = ProductBarcode(store_id=store.id, product_id=product.id, product_variant_id=primary.id, barcode=source["barcode"], barcode_type=source["barcode_type"], manufacturer_barcode=source["manufacturer_barcode"], package_quantity=source["package_quantity"], scan_unit=source["scan_unit"], inventory_unit=source["inventory_unit"], base_unit_conversion=source["base_unit_conversion"], sale_mode=source["sale_mode"], mrp=Decimal(source["mrp"]) if source.get("mrp") else None, default_selling_price=Decimal(source["default_selling_price"]) if source.get("default_selling_price") else None, active=source["active"], verified=True, verified_by=user.id, verified_at=datetime.now(timezone.utc))
            self.db.add(mapping); self.db.flush()
            for _, variant in targets:
                self.db.add(ProductBarcodeVariantTarget(store_id=store.id, product_barcode_id=mapping.id, product_variant_id=variant.id, created_by=user.id))

    def _post_opening_stock(self, package: dict[str, Any], store: Store, user: User, resolved: dict[str, tuple[Product, ProductVariant]]) -> list[StockHistory]:
        if package["mode"] != CATALOG_AND_OPENING_STOCK:
            return []
        poster = OpeningStockImportService(self.db)
        reference, request_id = f"TEST-CATALOG-MIGRATION:{package['package_id']}", f"catalog-migration:{package['package_id']}"
        movements: list[StockHistory] = []
        for stock in package["opening_stock"]:
            quantity = int(stock["quantity"])
            if quantity == 0:
                continue
            product, variant = resolved[stock["variant_key"]]
            _, movement = poster.post_migration_opening_stock(product=product, variant=variant, store_id=store.id, quantity=quantity, unit_cost=Decimal(stock["unit_cost"]), current_user=user, reference=reference, request_id=request_id)
            movements.append(movement)
        return movements

    def _restore_package_product_pricing(self, package: dict[str, Any], store: Store, *, completed_import_repair: bool = False) -> list[str]:
        """Make the package's product-level price fields authoritative again.

        Inventory cost lives on exact variants and cost lots.  The aggregate
        product purchase price remains catalog metadata for package imports.
        A completed-import repair is fail-closed unless the only discrepancy is
        product purchase price; it must never be used to silently rewrite MRP
        or selling prices after the fact.
        """
        products = (
            self.db.query(Product)
            .options(joinedload(Product.category), joinedload(Product.subcategory), joinedload(Product.brand))
            .filter(Product.store_id == store.id)
            .all()
        )
        by_key: dict[str, list[Product]] = defaultdict(list)
        for product in products:
            by_key[product_key({"category": product.category.name, "subcategory": product.subcategory.name, "brand": product.brand.name, "name": product.name, "sku": product.sku})].append(product)
        changed: list[str] = []
        for source in package["catalog"]["products"]:
            key = product_key(source)
            matches = by_key[key]
            if len(matches) != 1:
                raise MigrationSafetyError(f"Package product {key} is not uniquely present for price reconciliation.")
            product = matches[0]
            expected_mrp = Decimal(source["mrp"]) if source.get("mrp") else None
            expected_selling = Decimal(source["selling_price"])
            expected_purchase = Decimal(source["purchase_cost"])
            if completed_import_repair and (product.mrp != expected_mrp or product.selling_price != expected_selling):
                raise MigrationSafetyError("Completed-import reconciliation refuses non-purchase-price catalog differences.")
            if not completed_import_repair:
                product.mrp = expected_mrp
                product.selling_price = expected_selling
            if product.purchase_price != expected_purchase:
                product.purchase_price = expected_purchase
                changed.append(key)
        return changed

    def _verify_post_import(self, package: dict[str, Any], store: Store, movements: Iterable[StockHistory]) -> None:
        if package["mode"] != CATALOG_AND_OPENING_STOCK:
            return
        imported = sum(int(stock["quantity"]) for stock in package["opening_stock"])
        posted = sum(movement.qty for movement in movements)
        reference = f"TEST-CATALOG-MIGRATION:{package['package_id']}"
        ledger_total = self.db.query(func.coalesce(func.sum(StockHistory.qty), 0)).filter(StockHistory.store_id == store.id, StockHistory.reference == reference).scalar()
        if imported != posted or imported != ledger_total:
            raise MigrationSafetyError("Opening-stock verification failed; transaction will roll back.")
