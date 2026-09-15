"""Persist quick purchases, item discounts, accepted returns and exchanges.

Additive only: existing transaction amounts and stock history are unchanged.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

revision = "20260909_0050"
down_revision = "20260909_0049"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("purchases", sa.Column("entry_type", sa.String(20), nullable=False, server_default="FORMAL"))
    op.add_column("sales", sa.Column("payment_reference", sa.String(140)))
    op.add_column("sales", sa.Column("exchange_return_id", pg.UUID(as_uuid=True)))
    op.create_foreign_key("fk_sales_exchange_return", "sales", "sale_returns", ["exchange_return_id"], ["id"], ondelete="RESTRICT")
    op.create_unique_constraint("uq_sales_exchange_return", "sales", ["exchange_return_id"])
    op.add_column("sale_items", sa.Column("discount_type", sa.String(20), nullable=False, server_default="NONE"))
    op.add_column("sale_items", sa.Column("discount_value", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("sale_items", sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("sale_items", sa.Column("brand_snapshot", sa.String(120)))
    op.add_column("sale_return_items", sa.Column("restock", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_table("purchase_returns",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("store_id", pg.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("purchase_id", pg.UUID(as_uuid=True), sa.ForeignKey("purchases.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("supplier_id", pg.UUID(as_uuid=True), sa.ForeignKey("suppliers.id", ondelete="RESTRICT")),
        sa.Column("reason", sa.String(300), nullable=False), sa.Column("credit_note", sa.String(140)),
        sa.Column("credit_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_by", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    for column in ("store_id", "purchase_id", "supplier_id"):
        op.create_index(f"ix_purchase_returns_{column}", "purchase_returns", [column])
    op.create_table("purchase_return_items",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("purchase_return_id", pg.UUID(as_uuid=True), sa.ForeignKey("purchase_returns.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("purchase_item_id", pg.UUID(as_uuid=True), sa.ForeignKey("purchase_items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("product_variant_id", pg.UUID(as_uuid=True), sa.ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False), sa.Column("credit_amount", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint("quantity > 0 AND credit_amount >= 0", name="ck_purchase_return_item_amounts"))
    for column in ("purchase_return_id", "purchase_item_id"):
        op.create_index(f"ix_purchase_return_items_{column}", "purchase_return_items", [column])


def downgrade():
    # Removing these tables would destroy stock/financial evidence.
    raise RuntimeError("Retain return history. Roll back the application or restore a verified backup; do not drop transaction evidence.")
