"""add variant-level inventory, pricing, and cost lots

Revision ID: 20260729_0022
Revises: 20260728_0021
Create Date: 2026-07-28
"""

from decimal import Decimal
from typing import Optional
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260729_0022"
down_revision = "20260728_0021"
branch_labels = None
depends_on = None


def _token(value: Optional[object]) -> str:
    return "".join(character for character in str(value or "").upper() if character.isalnum()) or "STD"


def _identity(product_id: object, size: Optional[object], color: Optional[object], style: Optional[object], mrp: Optional[object], price: object) -> str:
    return "|".join((str(product_id), str(size or "").strip().casefold(), str(color or "").strip().casefold(), str(style or "").strip().casefold(), f"{Decimal(mrp or 0):.2f}", f"{Decimal(price):.2f}"))


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.add_column("product_variants", sa.Column("store_id", uuid, nullable=True))
    op.add_column("product_variants", sa.Column("style_code", sa.String(length=80), nullable=True))
    op.add_column("product_variants", sa.Column("model_number", sa.String(length=120), nullable=True))
    op.add_column("product_variants", sa.Column("manufacturer_sku", sa.String(length=120), nullable=True))
    op.add_column("product_variants", sa.Column("internal_sku", sa.String(length=120), nullable=True))
    op.add_column("product_variants", sa.Column("barcode", sa.String(length=80), nullable=True))
    op.add_column("product_variants", sa.Column("identity_key", sa.String(length=500), nullable=True))
    op.add_column("product_variants", sa.Column("mrp", sa.Numeric(12, 2), nullable=True))
    op.add_column("product_variants", sa.Column("selling_price", sa.Numeric(12, 2), nullable=True))
    op.add_column("product_variants", sa.Column("last_purchase_cost", sa.Numeric(12, 2), nullable=True))
    op.add_column("product_variants", sa.Column("average_cost", sa.Numeric(12, 2), nullable=True))
    op.add_column("product_variants", sa.Column("current_stock", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("product_variants", sa.Column("classification_review_required", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("product_variants", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("product_variants", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("purchase_items", sa.Column("product_variant_id", uuid, nullable=True))
    op.add_column("purchase_items", sa.Column("internal_sku", sa.String(length=120), nullable=True))
    op.add_column("purchase_items", sa.Column("style_code", sa.String(length=80), nullable=True))
    op.add_column("sale_items", sa.Column("product_variant_id", uuid, nullable=True))
    op.add_column("sale_items", sa.Column("style_snapshot", sa.String(length=80), nullable=True))
    op.add_column("sale_items", sa.Column("mrp_snapshot", sa.Numeric(12, 2), nullable=True))
    op.add_column("stock_history", sa.Column("product_variant_id", uuid, nullable=True))
    op.add_column("stock_history", sa.Column("purchase_cost_lot_id", uuid, nullable=True))
    op.add_column("stock_history", sa.Column("unit_cost", sa.Numeric(12, 2), nullable=True))
    op.drop_constraint("uq_product_variants_combination", "product_variants", type_="unique")

    op.create_table(
        "inventory_cost_lots",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("store_id", uuid, sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_variant_id", uuid, sa.ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purchase_id", uuid, sa.ForeignKey("purchases.id", ondelete="SET NULL")),
        sa.Column("purchase_item_id", uuid, sa.ForeignKey("purchase_items.id", ondelete="SET NULL"), unique=True),
        sa.Column("supplier_id", uuid, sa.ForeignKey("suppliers.id", ondelete="SET NULL")),
        sa.Column("received_quantity", sa.Integer(), nullable=False),
        sa.Column("remaining_quantity", sa.Integer(), nullable=False),
        sa.Column("unit_purchase_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("allocated_landed_cost", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("effective_unit_cost", sa.Numeric(12, 2), nullable=False),
        sa.Column("received_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("lot_reference", sa.String(length=180)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    bind = op.get_bind()
    base_variants = bind.execute(sa.text("""
        SELECT variant.id, variant.product_id, product.store_id, variant.size, variant.color,
               product.name, product.mrp, product.selling_price, product.purchase_price
        FROM product_variants AS variant
        JOIN products AS product ON product.id = variant.product_id
    """)).mappings().all()
    for row in base_variants:
        if row["store_id"] is None:
            continue
        prefix = "".join(part[0] for part in str(row["name"]).split() if part)[:4].upper() or "RF"
        price = Decimal(row["selling_price"] or 0)
        mrp = Decimal(row["mrp"] or price)
        sku = f"{prefix}-{_token(row['size'])}-{mrp.quantize(Decimal('1'))}-A"
        bind.execute(sa.text("""
            UPDATE product_variants
            SET store_id = :store_id, internal_sku = :sku, barcode = :barcode,
                identity_key = :identity_key, mrp = :mrp, selling_price = :price,
                last_purchase_cost = :cost, average_cost = :cost, updated_at = now()
            WHERE id = :id
        """), {"id": row["id"], "store_id": row["store_id"], "sku": sku, "barcode": f"RFV{uuid4().hex[:14].upper()}", "identity_key": _identity(row["product_id"], row["size"], row["color"], "A", mrp, price), "mrp": mrp, "price": price, "cost": row["purchase_price"] or 0})

    oe_products = bind.execute(sa.text("SELECT id FROM products WHERE lower(name) = 'oe panties'" )).scalars().all()
    if oe_products:
        bind.execute(sa.text("DELETE FROM product_variants WHERE product_id = ANY(:product_ids)"), {"product_ids": oe_products})
        rows = bind.execute(sa.text("""
            SELECT item.id, item.purchase_id, item.product_id, product.store_id, product.name,
                   purchase.supplier_id, purchase.purchase_date, item.size, item.color,
                   item.quantity, item.purchase_price, item.landed_unit_cost, item.mrp,
                   COALESCE(item.selling_price, item.mrp, product.selling_price) AS selling_price,
                   item.supplier_product_code, item.barcode, item.batch_number
            FROM purchase_items AS item
            JOIN purchases AS purchase ON purchase.id = item.purchase_id
            JOIN products AS product ON product.id = item.product_id
            WHERE item.product_id = ANY(:product_ids)
            ORDER BY item.created_at, item.id
        """), {"product_ids": oe_products}).mappings().all()
        variants: dict[str, dict] = {}
        style_counters: dict[tuple[object, str, str], int] = {}
        for row in rows:
            size = row["size"] or "Standard"
            color = row["color"] or ""
            pair = (row["product_id"], str(size).casefold(), str(color).casefold())
            price = Decimal(row["selling_price"] or 0)
            mrp = Decimal(row["mrp"] or price)
            price_key = (pair, mrp, price)
            if price_key not in variants:
                style_counters[pair] = style_counters.get(pair, 0) + 1
                style = chr(64 + style_counters[pair])
                prefix = "".join(part[0] for part in str(row["name"]).split() if part)[:4].upper() or "RF"
                internal_sku = f"{prefix}-{_token(size)}-{mrp.quantize(Decimal('1'))}-{style}"
                variant_id = uuid4()
                variants[price_key] = {"id": variant_id, "style": style, "sku": internal_sku, "stock": 0, "cost_value": Decimal("0"), "cost_quantity": 0}
                bind.execute(sa.text("""
                    INSERT INTO product_variants (id, store_id, product_id, color, size, style_code, manufacturer_sku, internal_sku, barcode, identity_key, mrp, selling_price, last_purchase_cost, average_cost, current_stock, classification_review_required, is_active, created_at, updated_at)
                    VALUES (:id, :store_id, :product_id, :color, :size, :style, :manufacturer_sku, :sku, :barcode, :identity_key, :mrp, :price, :cost, :cost, 0, true, true, now(), now())
                """), {"id": variant_id, "store_id": row["store_id"], "product_id": row["product_id"], "color": color or None, "size": size, "style": style, "manufacturer_sku": row["supplier_product_code"], "sku": internal_sku, "barcode": row["barcode"] or f"RFV{uuid4().hex[:14].upper()}", "identity_key": _identity(row["product_id"], size, color, style, mrp, price), "mrp": mrp, "price": price, "cost": row["landed_unit_cost"] or row["purchase_price"]})
            variant = variants[price_key]
            quantity = int(row["quantity"] or 0)
            unit_cost = Decimal(row["landed_unit_cost"] or row["purchase_price"] or 0)
            variant["stock"] += quantity
            variant["cost_quantity"] += quantity
            variant["cost_value"] += unit_cost * quantity
            bind.execute(sa.text("""
                UPDATE purchase_items
                SET product_variant_id = :variant_id, style_code = :style, internal_sku = :sku,
                    selling_price = :price
                WHERE id = :item_id
            """), {"variant_id": variant["id"], "style": variant["style"], "sku": variant["sku"], "price": price, "item_id": row["id"]})
            bind.execute(sa.text("""
                INSERT INTO inventory_cost_lots (id, store_id, product_variant_id, purchase_id, purchase_item_id, supplier_id, received_quantity, remaining_quantity, unit_purchase_cost, allocated_landed_cost, effective_unit_cost, received_date, lot_reference, created_at)
                VALUES (:id, :store_id, :variant_id, :purchase_id, :purchase_item_id, :supplier_id, :quantity, :quantity, :purchase_price, 0, :unit_cost, :received_date, :lot_reference, now())
            """), {"id": uuid4(), "store_id": row["store_id"], "variant_id": variant["id"], "purchase_id": row["purchase_id"], "purchase_item_id": row["id"], "supplier_id": row["supplier_id"], "quantity": quantity, "purchase_price": row["purchase_price"], "unit_cost": unit_cost, "received_date": row["purchase_date"], "lot_reference": row["batch_number"]})
        for variant in variants.values():
            average = (variant["cost_value"] / variant["cost_quantity"]).quantize(Decimal("0.01")) if variant["cost_quantity"] else Decimal("0")
            bind.execute(sa.text("UPDATE product_variants SET current_stock = :stock, average_cost = :average, last_purchase_cost = :average WHERE id = :id"), {"id": variant["id"], "stock": variant["stock"], "average": average})

    op.create_foreign_key("fk_product_variants_store_id", "product_variants", "stores", ["store_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_purchase_items_product_variant_id", "purchase_items", "product_variants", ["product_variant_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_sale_items_product_variant_id", "sale_items", "product_variants", ["product_variant_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_stock_history_product_variant_id", "stock_history", "product_variants", ["product_variant_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_stock_history_purchase_cost_lot_id", "stock_history", "inventory_cost_lots", ["purchase_cost_lot_id"], ["id"], ondelete="SET NULL")
    op.alter_column("product_variants", "store_id", nullable=False)
    op.alter_column("product_variants", "internal_sku", nullable=False)
    op.alter_column("product_variants", "barcode", nullable=False)
    op.alter_column("product_variants", "identity_key", nullable=False)
    op.alter_column("product_variants", "selling_price", nullable=False)
    op.alter_column("product_variants", "last_purchase_cost", nullable=False)
    op.alter_column("product_variants", "average_cost", nullable=False)
    op.create_unique_constraint("uq_product_variants_store_identity", "product_variants", ["store_id", "identity_key"])
    op.create_unique_constraint("uq_product_variants_store_internal_sku", "product_variants", ["store_id", "internal_sku"])
    op.create_unique_constraint("uq_product_variants_store_barcode", "product_variants", ["store_id", "barcode"])
    op.create_index("ix_product_variants_store_id", "product_variants", ["store_id"])
    op.create_index("ix_inventory_cost_lots_store_id", "inventory_cost_lots", ["store_id"])
    op.create_index("ix_inventory_cost_lots_product_variant_id", "inventory_cost_lots", ["product_variant_id"])
    op.execute("ALTER TABLE product_variants ALTER COLUMN current_stock DROP DEFAULT")
    op.execute("ALTER TABLE product_variants ALTER COLUMN classification_review_required DROP DEFAULT")
    op.execute("ALTER TABLE product_variants ALTER COLUMN is_active DROP DEFAULT")


def downgrade() -> None:
    op.drop_table("inventory_cost_lots")
    op.drop_constraint("fk_stock_history_purchase_cost_lot_id", "stock_history", type_="foreignkey")
    op.drop_constraint("fk_stock_history_product_variant_id", "stock_history", type_="foreignkey")
    op.drop_constraint("fk_sale_items_product_variant_id", "sale_items", type_="foreignkey")
    op.drop_constraint("fk_purchase_items_product_variant_id", "purchase_items", type_="foreignkey")
    op.drop_constraint("fk_product_variants_store_id", "product_variants", type_="foreignkey")
    op.drop_constraint("uq_product_variants_store_barcode", "product_variants", type_="unique")
    op.drop_constraint("uq_product_variants_store_internal_sku", "product_variants", type_="unique")
    op.drop_constraint("uq_product_variants_store_identity", "product_variants", type_="unique")
    op.create_unique_constraint("uq_product_variants_combination", "product_variants", ["product_id", "color", "size"])
    for column in ("purchase_cost_lot_id", "product_variant_id", "unit_cost"):
        op.drop_column("stock_history", column)
    for column in ("product_variant_id", "style_snapshot", "mrp_snapshot"):
        op.drop_column("sale_items", column)
    for column in ("product_variant_id", "internal_sku", "style_code"):
        op.drop_column("purchase_items", column)
    for column in ("updated_at", "is_active", "classification_review_required", "current_stock", "average_cost", "last_purchase_cost", "selling_price", "mrp", "identity_key", "barcode", "internal_sku", "manufacturer_sku", "model_number", "style_code", "store_id"):
        op.drop_column("product_variants", column)
