"""Add specific staff roles, shop settings, audit trail and daily cash closing.

Additive only: legacy STAFF and all historical records remain intact.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260909_0049"
down_revision = "20260904_0048"
branch_labels = None
depends_on = None


def upgrade():
    for role in ("CASHIER", "STOCK_STAFF", "ACCOUNTANT", "VIEWER"):
        op.execute(f"ALTER TYPE user_role ADD VALUE IF NOT EXISTS '{role}'")
    uuid = postgresql.UUID(as_uuid=True)
    op.create_table("store_preferences",
        sa.Column("store_id", uuid, sa.ForeignKey("stores.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("settings_json", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("updated_by", uuid, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_table("operations_audits",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("store_id", uuid, sa.ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("reference", sa.String(180)), sa.Column("reason", sa.String(500)),
        sa.Column("before_data", postgresql.JSONB()), sa.Column("after_data", postgresql.JSONB()),
        sa.Column("request_id", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    for column in ("store_id", "action", "created_at"):
        op.create_index(f"ix_operations_audits_{column}", "operations_audits", [column])
    op.create_table("day_closings",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("store_id", uuid, sa.ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("opening_cash", sa.Numeric(14, 2), nullable=False),
        sa.Column("actual_cash", sa.Numeric(14, 2), nullable=False),
        sa.Column("expected_cash", sa.Numeric(14, 2), nullable=False),
        sa.Column("difference", sa.Numeric(14, 2), nullable=False),
        sa.Column("summary_json", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="SUBMITTED"),
        sa.Column("notes", sa.String(500)),
        sa.Column("created_by", uuid, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("approved_by", uuid, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("store_id", "business_date", name="uq_day_closing_store_date"))
    op.create_index("ix_day_closings_store_id", "day_closings", ["store_id"])
    op.create_index("ix_day_closings_business_date", "day_closings", ["business_date"])


def downgrade():
    # Retain financial closing/audit history and settings on application rollback.
    # Removing enum values would invalidate existing users; recovery is forward.
    pass
