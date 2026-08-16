"""support shared barcodes with explicit variant targets

Revision ID: 20260814_0041
Revises: 20260804_0040
Create Date: 2026-08-14
"""

from __future__ import annotations

from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260814_0041"
down_revision = "20260804_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        "product_barcode_variant_targets",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("store_id", uuid, sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_barcode_id", uuid, sa.ForeignKey("product_barcodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_variant_id", uuid, sa.ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_by", uuid, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("product_barcode_id", "product_variant_id", name="uq_barcode_variant_target"),
    )
    op.create_index("ix_product_barcode_variant_targets_store_id", "product_barcode_variant_targets", ["store_id"])
    op.create_index("ix_product_barcode_variant_targets_product_barcode_id", "product_barcode_variant_targets", ["product_barcode_id"])
    op.create_index("ix_product_barcode_variant_targets_product_variant_id", "product_barcode_variant_targets", ["product_variant_id"])

    # Every existing mapping begins with one explicit target. Some legacy
    # mappings have no verified_by user, which is intentionally retained as
    # null rather than inventing an audit identity.
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, store_id, product_variant_id, verified_by FROM product_barcodes")).mappings()
    for row in rows:
        bind.execute(
            sa.text(
                """
                INSERT INTO product_barcode_variant_targets
                    (id, store_id, product_barcode_id, product_variant_id, created_by, created_at)
                VALUES (:id, :store_id, :barcode_id, :variant_id, :created_by, now())
                """
            ),
            {"id": uuid4(), "store_id": row["store_id"], "barcode_id": row["id"], "variant_id": row["product_variant_id"], "created_by": row["verified_by"]},
        )


def downgrade() -> None:
    op.drop_index("ix_product_barcode_variant_targets_product_variant_id", table_name="product_barcode_variant_targets")
    op.drop_index("ix_product_barcode_variant_targets_product_barcode_id", table_name="product_barcode_variant_targets")
    op.drop_index("ix_product_barcode_variant_targets_store_id", table_name="product_barcode_variant_targets")
    op.drop_table("product_barcode_variant_targets")
