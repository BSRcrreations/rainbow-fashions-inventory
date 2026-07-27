"""add sale edit, return, void, and audit workflow

Revision ID: 20260724_0006
Revises: 20260718_0005
Create Date: 2026-07-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260724_0006"
down_revision = "20260718_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sale_status = postgresql.ENUM(
        "COMPLETED", "EDITED", "PARTIALLY_RETURNED", "RETURNED", "VOIDED", name="sale_status", create_type=False
    )
    sale_status.create(op.get_bind(), checkfirst=True)
    op.add_column("sales", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column("sales", sa.Column("status", sale_status, server_default="COMPLETED", nullable=False))
    op.add_column("sales", sa.Column("version", sa.Integer(), server_default="1", nullable=False))
    op.add_column("sales", sa.Column("edited_at", sa.DateTime(timezone=True)))
    op.add_column("sales", sa.Column("edited_by", postgresql.UUID(as_uuid=True)))
    op.add_column("sales", sa.Column("edit_reason", sa.String(300)))
    op.add_column("sales", sa.Column("voided_at", sa.DateTime(timezone=True)))
    op.add_column("sales", sa.Column("voided_by", postgresql.UUID(as_uuid=True)))
    op.add_column("sales", sa.Column("void_reason", sa.String(300)))
    op.create_foreign_key("fk_sales_edited_by", "sales", "users", ["edited_by"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_sales_voided_by", "sales", "users", ["voided_by"], ["id"], ondelete="SET NULL")
    op.create_index("ix_sales_status", "sales", ["status"])

    for column, length in (("sku_snapshot", 80), ("barcode_snapshot", 80), ("size_snapshot", 60), ("color_snapshot", 80)):
        op.add_column("sale_items", sa.Column(column, sa.String(length)))
    op.execute(
        """
        UPDATE sale_items si SET
          sku_snapshot = p.sku,
          barcode_snapshot = p.barcode,
          size_snapshot = p.size,
          color_snapshot = p.color
        FROM products p WHERE p.id = si.product_id
        """
    )

    op.create_table(
        "sale_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("reason", sa.String(300)),
        sa.Column("performed_by", postgresql.UUID(as_uuid=True)),
        sa.Column("before_data", postgresql.JSONB()),
        sa.Column("after_data", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["performed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sale_audits_sale_id", "sale_audits", ["sale_id"])
    op.create_table(
        "sale_returns",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("sale_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.String(300), nullable=False),
        sa.Column("refund_method", sa.String(40)),
        sa.Column("refund_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["sale_id"], ["sales.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sale_returns_sale_id", "sale_returns", ["sale_id"])
    op.create_index("ix_sale_returns_store_id", "sale_returns", ["store_id"])
    op.create_table(
        "sale_return_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("sale_return_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sale_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("refund_amount", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_sale_return_items_quantity_positive"),
        sa.ForeignKeyConstraint(["sale_return_id"], ["sale_returns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sale_item_id"], ["sale_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sale_return_items_sale_return_id", "sale_return_items", ["sale_return_id"])
    op.create_index("ix_sale_return_items_sale_item_id", "sale_return_items", ["sale_item_id"])


def downgrade() -> None:
    op.drop_index("ix_sale_return_items_sale_item_id", table_name="sale_return_items")
    op.drop_index("ix_sale_return_items_sale_return_id", table_name="sale_return_items")
    op.drop_table("sale_return_items")
    op.drop_index("ix_sale_returns_store_id", table_name="sale_returns")
    op.drop_index("ix_sale_returns_sale_id", table_name="sale_returns")
    op.drop_table("sale_returns")
    op.drop_index("ix_sale_audits_sale_id", table_name="sale_audits")
    op.drop_table("sale_audits")
    for column in ("color_snapshot", "size_snapshot", "barcode_snapshot", "sku_snapshot"):
        op.drop_column("sale_items", column)
    op.drop_index("ix_sales_status", table_name="sales")
    op.drop_constraint("fk_sales_voided_by", "sales", type_="foreignkey")
    op.drop_constraint("fk_sales_edited_by", "sales", type_="foreignkey")
    for column in ("void_reason", "voided_by", "voided_at", "edit_reason", "edited_by", "edited_at", "version", "status", "updated_at"):
        op.drop_column("sales", column)
    postgresql.ENUM(name="sale_status").drop(op.get_bind(), checkfirst=True)
