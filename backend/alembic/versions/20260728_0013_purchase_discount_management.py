"""add auditable purchase discount management

Revision ID: 20260728_0013
Revises: 20260727_0012
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260728_0013"
down_revision = "20260727_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("purchases", sa.Column("invoice_discount_type", sa.String(40), server_default="NONE", nullable=False))
    op.add_column("purchases", sa.Column("invoice_discount_percentage", sa.Numeric(7, 4), server_default="0", nullable=False))
    op.add_column("purchases", sa.Column("invoice_discount_amount", sa.Numeric(18, 2), server_default="0", nullable=False))
    op.add_column("purchases", sa.Column("invoice_discount_reason", sa.String(500)))
    op.add_column("purchases", sa.Column("invoice_discount_allocation_method", sa.String(40), server_default="BY_ITEM_VALUE", nullable=False))

    op.add_column("purchase_items", sa.Column("list_unit_price", sa.Numeric(18, 2), server_default="0", nullable=False))
    op.add_column("purchase_items", sa.Column("invoiced_unit_price", sa.Numeric(18, 2)))
    op.add_column("purchase_items", sa.Column("discount_type", sa.String(40), server_default="NONE", nullable=False))
    op.add_column("purchase_items", sa.Column("discount_percentage", sa.Numeric(7, 4), server_default="0", nullable=False))
    op.add_column("purchase_items", sa.Column("discount_per_unit", sa.Numeric(18, 2), server_default="0", nullable=False))
    op.add_column("purchase_items", sa.Column("discount_amount", sa.Numeric(18, 2), server_default="0", nullable=False))
    op.add_column("purchase_items", sa.Column("discount_reason", sa.String(500)))
    op.add_column("purchase_items", sa.Column("discount_source", sa.String(40), server_default="INVOICE_EXTRACTED", nullable=False))
    op.add_column("purchase_items", sa.Column("free_quantity", sa.Numeric(18, 4), server_default="0", nullable=False))
    op.add_column("purchase_items", sa.Column("chargeable_quantity", sa.Numeric(18, 4), server_default="0", nullable=False))
    op.add_column("purchase_items", sa.Column("accepted_quantity", sa.Numeric(18, 4), server_default="0", nullable=False))
    op.add_column("purchase_items", sa.Column("gross_amount", sa.Numeric(18, 2), server_default="0", nullable=False))
    op.add_column("purchase_items", sa.Column("taxable_amount", sa.Numeric(18, 2), server_default="0", nullable=False))
    op.add_column("purchase_items", sa.Column("net_line_amount", sa.Numeric(18, 2), server_default="0", nullable=False))
    op.add_column("purchase_items", sa.Column("effective_unit_cost", sa.Numeric(18, 2), server_default="0", nullable=False))
    op.add_column("purchase_items", sa.Column("landed_unit_cost", sa.Numeric(18, 2), server_default="0", nullable=False))
    op.add_column("purchase_items", sa.Column("allocated_invoice_discount", sa.Numeric(18, 2), server_default="0", nullable=False))
    op.add_column("purchase_items", sa.Column("promotion_id", postgresql.UUID(as_uuid=True)))
    op.add_column("purchase_items", sa.Column("discount_rule_id", postgresql.UUID(as_uuid=True)))
    op.add_column("purchase_items", sa.Column("discount_verified", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("purchase_items", sa.Column("discount_verified_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")))
    op.add_column("purchase_items", sa.Column("discount_verified_at", sa.DateTime(timezone=True)))

    # Preserve historical invoice values: legacy price and discount columns remain
    # untouched, while the new values explicitly describe the same calculation.
    op.execute("""
        UPDATE purchase_items
        SET list_unit_price = purchase_price,
            invoiced_unit_price = purchase_price,
            chargeable_quantity = quantity,
            accepted_quantity = quantity,
            gross_amount = quantity * purchase_price,
            discount_amount = discount,
            taxable_amount = GREATEST((quantity * purchase_price) - discount, 0),
            net_line_amount = line_total,
            effective_unit_cost = CASE WHEN quantity > 0 THEN GREATEST((quantity * purchase_price) - discount, 0) / quantity ELSE 0 END,
            landed_unit_cost = CASE WHEN quantity > 0 THEN GREATEST((quantity * purchase_price) - discount, 0) / quantity ELSE 0 END
    """)
    op.execute("""
        UPDATE purchase_items
        SET discount_type = CASE WHEN discount > 0 THEN 'FIXED_PER_LINE' ELSE 'NONE' END
    """)


def downgrade() -> None:
    for column in (
        "discount_verified_at", "discount_verified_by", "discount_verified", "discount_rule_id", "promotion_id",
        "allocated_invoice_discount", "landed_unit_cost", "effective_unit_cost", "net_line_amount", "taxable_amount",
        "gross_amount", "accepted_quantity", "chargeable_quantity", "free_quantity", "discount_source", "discount_reason",
        "discount_amount", "discount_per_unit", "discount_percentage", "discount_type", "invoiced_unit_price", "list_unit_price",
    ):
        op.drop_column("purchase_items", column)
    for column in (
        "invoice_discount_allocation_method", "invoice_discount_reason", "invoice_discount_amount",
        "invoice_discount_percentage", "invoice_discount_type",
    ):
        op.drop_column("purchases", column)
