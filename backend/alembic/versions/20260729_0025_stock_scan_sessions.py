"""add persistent barcode stock scan sessions

Revision ID: 20260729_0025
Revises: 20260729_0024
Create Date: 2026-07-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260729_0025"
down_revision = "20260729_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    # PostgreSQL ENUM values are append-only. These names make stock-count
    # movements explicit without changing historic generic adjustments.
    with op.get_context().autocommit_block():
        for value in ("OPENING_STOCK", "STOCK_COUNT_IN", "STOCK_COUNT_OUT"):
            bind.execute(sa.text(f"ALTER TYPE stock_movement_type ADD VALUE IF NOT EXISTS '{value}'"))

    scan_mode = postgresql.ENUM(
        "PURCHASE_RECEIVING", "OPENING_STOCK", "PHYSICAL_COUNT", "STOCK_ADJUSTMENT", "STOCK_TRANSFER",
        name="stock_scan_mode",
    )
    scan_status = postgresql.ENUM("DRAFT", "IN_PROGRESS", "REVIEW_REQUIRED", "CONFIRMED", "CANCELLED", name="stock_scan_status")
    quantity_mode = postgresql.ENUM("INCREMENT", "QUANTITY_ENTRY", name="stock_scan_quantity_mode")
    scan_mode.create(bind, checkfirst=True)
    scan_status.create(bind, checkfirst=True)
    quantity_mode.create(bind, checkfirst=True)
    scan_mode_column = postgresql.ENUM(
        "PURCHASE_RECEIVING", "OPENING_STOCK", "PHYSICAL_COUNT", "STOCK_ADJUSTMENT", "STOCK_TRANSFER",
        name="stock_scan_mode", create_type=False,
    )
    scan_status_column = postgresql.ENUM("DRAFT", "IN_PROGRESS", "REVIEW_REQUIRED", "CONFIRMED", "CANCELLED", name="stock_scan_status", create_type=False)
    quantity_mode_column = postgresql.ENUM("INCREMENT", "QUANTITY_ENTRY", name="stock_scan_quantity_mode", create_type=False)
    uuid = postgresql.UUID(as_uuid=True)

    op.create_table(
        "stock_scan_sessions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("store_id", uuid, sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mode", scan_mode_column, nullable=False),
        sa.Column("status", scan_status_column, nullable=False, server_default="IN_PROGRESS"),
        sa.Column("quantity_mode", quantity_mode_column, nullable=False, server_default="INCREMENT"),
        sa.Column("purchase_id", uuid, sa.ForeignKey("purchases.id", ondelete="SET NULL")),
        sa.Column("location_name", sa.String(length=120), nullable=False, server_default="Main store"),
        sa.Column("source_location_name", sa.String(length=120)),
        sa.Column("destination_location_name", sa.String(length=120)),
        sa.Column("reference", sa.String(length=180)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_by", uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("confirmed_by", uuid, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_stock_scan_sessions_store_id", "stock_scan_sessions", ["store_id"])
    op.create_index("ix_stock_scan_sessions_mode", "stock_scan_sessions", ["mode"])
    op.create_index("ix_stock_scan_sessions_status", "stock_scan_sessions", ["status"])
    op.create_index("ix_stock_scan_sessions_purchase_id", "stock_scan_sessions", ["purchase_id"])
    op.create_index("ix_stock_scan_sessions_created_at", "stock_scan_sessions", ["created_at"])

    op.create_table(
        "stock_scan_session_items",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("session_id", uuid, sa.ForeignKey("stock_scan_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", uuid, sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("product_variant_id", uuid, sa.ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("barcode", sa.String(length=80), nullable=False),
        sa.Column("scanned_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expected_quantity", sa.Integer()),
        sa.Column("difference_quantity", sa.Integer()),
        sa.Column("unit_cost", sa.Numeric(12, 2)),
        sa.Column("condition", sa.String(length=40), nullable=False, server_default="SELLABLE"),
        sa.Column("last_scanned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("session_id", "product_variant_id", name="uq_stock_scan_session_variant"),
    )
    op.create_index("ix_stock_scan_session_items_session_id", "stock_scan_session_items", ["session_id"])
    op.create_index("ix_stock_scan_session_items_product_id", "stock_scan_session_items", ["product_id"])
    op.create_index("ix_stock_scan_session_items_product_variant_id", "stock_scan_session_items", ["product_variant_id"])
    op.create_index("ix_stock_scan_session_items_last_scanned_at", "stock_scan_session_items", ["last_scanned_at"])


def downgrade() -> None:
    op.drop_table("stock_scan_session_items")
    op.drop_table("stock_scan_sessions")
    bind = op.get_bind()
    for enum_name in ("stock_scan_quantity_mode", "stock_scan_status", "stock_scan_mode"):
        postgresql.ENUM(name=enum_name).drop(bind, checkfirst=True)
    # PostgreSQL does not safely remove values from stock_movement_type; retain
    # the explicit historic values when rolling back session tables.
