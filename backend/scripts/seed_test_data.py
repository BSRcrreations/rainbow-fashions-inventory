#!/usr/bin/env python3
"""Create deterministic, non-production data for the inventory UAT database."""
from __future__ import annotations

import os
from decimal import Decimal
from uuid import NAMESPACE_URL, UUID, uuid5

from app.core.config import get_settings
from app.core.security import hash_password
from app.core.testing import assert_test_database
from app.database.session import SessionLocal
from app.models.brand import Brand
from app.models.category import Category
from app.models.enums import PricingType, StockMovementType, UserRole
from app.models.product import Product
from app.models.product_barcode import ProductBarcode
from app.models.product_inventory import ProductInventory
from app.models.product_variant import InventoryCostLot, ProductVariant
from app.models.stock_history import StockHistory
from app.models.store import Store
from app.models.subcategory import SubCategory
from app.models.user import User


def uid(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"rainbow-fashions-uat:{name}")


def record(db, model, record_id: UUID, **values):
    instance = db.get(model, record_id)
    if instance is None:
        instance = model(id=record_id, **values)
        db.add(instance)
    else:
        for key, value in values.items():
            setattr(instance, key, value)
    return instance


def testing_password() -> str:
    value = os.environ.get("UAT_TEST_PASSWORD", "")
    if not value or "CHANGE_ME" in value:
        raise RuntimeError("Set a testing-only UAT_TEST_PASSWORD before seeding UAT users.")
    return value


def main() -> None:
    settings = get_settings()
    database_name = assert_test_database(settings.app_env, settings.database_url)
    password_hash = hash_password(testing_password())
    db = SessionLocal()
    try:
        store = record(
            db,
            Store,
            uid("store"),
            name="Rainbow Fashions UAT",
            code="UAT",
            address="Isolated test environment only",
            phone="+91-0000000000",
            is_active=True,
            allow_test_data_purge=True,
        )
        db.flush()

        users = (
            ("owner", "UAT Owner", "owner.uat@rainbow.test", UserRole.OWNER),
            ("inventory", "UAT Inventory Staff", "inventory.uat@rainbow.test", UserRole.STAFF),
            ("cashier", "UAT Cashier", "cashier.uat@rainbow.test", UserRole.STAFF),
        )
        for key, full_name, email, role in users:
            record(
                db,
                User,
                uid(f"user:{key}"),
                store_id=store.id,
                full_name=full_name,
                email=email,
                password_hash=password_hash,
                role=role,
                is_active=True,
            )

        categories: dict[str, Category] = {}
        subcategories: dict[str, SubCategory] = {}
        for name in ("Leggings", "Bras", "Panties"):
            category = record(
                db,
                Category,
                uid(f"category:{name}"),
                store_id=store.id,
                name=name,
                description=f"UAT {name.lower()} catalog",
                is_active=True,
            )
            categories[name] = category
            subcategories[name] = record(
                db,
                SubCategory,
                uid(f"subcategory:{name}:general"),
                store_id=store.id,
                category_id=category.id,
                name="General",
                description="UAT default subcategory",
                is_active=True,
            )

        brands: dict[str, Brand] = {}
        for name, category_name in (("Prisma", "Leggings"), ("Fly Birds", "Leggings"), ("Twin Birds", "Bras"), ("Lovable", "Panties")):
            category = categories[category_name]
            brands[name] = record(
                db,
                Brand,
                uid(f"brand:{name}"),
                store_id=store.id,
                category_id=category.id,
                name=name,
                description=f"UAT brand: {name}",
                logo_url=None,
                is_active=True,
            )

        for brand_name in ("Prisma", "Fly Birds"):
            product_id = uid(f"product:full-leggings:{brand_name}")
            product = record(
                db,
                Product,
                product_id,
                store_id=store.id,
                category_id=categories["Leggings"].id,
                subcategory_id=subcategories["Leggings"].id,
                brand_id=brands[brand_name].id,
                sku=f"UAT-{brand_name.replace(' ', '-').upper()}-LEGGINGS",
                name="Full Leggings",
                size="S",
                color="Assorted",
                purchase_price=Decimal("250.00"),
                selling_price=Decimal("499.00"),
                pricing_type=PricingType.MRP,
                mrp=Decimal("499.00"),
                current_stock=120,
                minimum_stock=6,
                barcode=None,
                description="Deterministic UAT product. Do not use in production.",
                is_active=True,
                is_test_data=True,
            )
            for size in ("S", "M", "L", "XL", "2XL", "3XL"):
                key = f"{brand_name.replace(' ', '-').upper()}-{size}"
                variant_id = uid(f"variant:full-leggings:{brand_name}:{size}")
                variant = record(
                    db,
                    ProductVariant,
                    variant_id,
                    store_id=store.id,
                    product_id=product.id,
                    size=size,
                    color="Assorted",
                    style_code="UAT-LEG",
                    model_number=None,
                    manufacturer_sku=f"UAT-MFG-{key}",
                    internal_sku=f"UAT-{key}",
                    barcode=f"UAT-VAR-{key}",
                    identity_key=f"uat|full-leggings|{brand_name.lower()}|{size.lower()}|assorted",
                    mrp=Decimal("499.00"),
                    selling_price=Decimal("499.00"),
                    last_purchase_cost=Decimal("250.00"),
                    average_cost=Decimal("250.00"),
                    current_stock=20,
                    classification_review_required=False,
                    is_active=True,
                )
                record(
                    db,
                    ProductBarcode,
                    uid(f"barcode:{brand_name}:{size}"),
                    store_id=store.id,
                    product_id=product.id,
                    product_variant_id=variant.id,
                    barcode=f"UAT-MFG-{key}",
                    barcode_type="MANUFACTURER",
                    manufacturer_barcode=True,
                    package_quantity=1,
                    scan_unit="PIECE",
                    inventory_unit="PIECE",
                    base_unit_conversion=1,
                    sale_mode="PIECE_ONLY",
                    mrp=Decimal("499.00"),
                    default_selling_price=Decimal("499.00"),
                    active=True,
                    verified=True,
                    verified_by=uid("user:owner"),
                )
                record(
                    db,
                    InventoryCostLot,
                    uid(f"cost-lot:{brand_name}:{size}"),
                    store_id=store.id,
                    product_variant_id=variant.id,
                    purchase_id=None,
                    purchase_item_id=None,
                    supplier_id=None,
                    received_quantity=20,
                    remaining_quantity=20,
                    unit_purchase_cost=Decimal("250.00"),
                    allocated_landed_cost=Decimal("0.00"),
                    effective_unit_cost=Decimal("250.00"),
                    lot_reference=f"UAT-OPENING-{key}",
                )
                record(
                    db,
                    StockHistory,
                    uid(f"stock-history:opening:{brand_name}:{size}"),
                    product_id=product.id,
                    product_variant_id=variant.id,
                    purchase_cost_lot_id=uid(f"cost-lot:{brand_name}:{size}"),
                    unit_cost=Decimal("250.00"),
                    store_id=store.id,
                    movement_type=StockMovementType.OPENING_STOCK,
                    qty=20,
                    before_stock=0,
                    after_stock=20,
                    reference=f"UAT-OPENING-{key}",
                    request_id=f"uat-opening-{key.lower()}",
                    purchase_id=None,
                    purchase_item_id=None,
                    sale_id=None,
                    sale_item_id=None,
                    correction_of_id=None,
                    correction_reason=None,
                    correction_notes=None,
                    created_by=uid("user:owner"),
                )
            record(
                db,
                ProductInventory,
                uid(f"inventory:full-leggings:{brand_name}"),
                product_id=product.id,
                store_id=store.id,
                current_stock=120,
                minimum_stock=6,
            )

        db.commit()
        print(f"Seeded isolated UAT data into {database_name}: 3 users, 3 categories, 4 brands, 2 products, 12 variants.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
