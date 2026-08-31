"""Repair missing audited destructive-action schema on databases stamped through 0044.

Revision ID: 20260825_0045
Revises: 20260824_0044
Create Date: 2026-08-25

The original 20260728_0017 migration introduced this schema.  Some legacy
databases were later recorded at newer revisions without its four tables.
This forward repair is deliberately additive: it creates only absent tables
and refuses to guess how to repair a partially-created table.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260825_0045"
down_revision = "20260824_0044"
branch_labels = None
depends_on = None


_REQUIRED_COLUMNS = {
    "store_security_settings": {
        "store_id",
        "delete_password_hash",
        "require_password_for_sale_delete",
        "require_password_for_purchase_delete",
        "updated_by",
        "updated_at",
    },
    "delete_password_attempts": {"id", "store_id", "user_id", "attempted_at"},
    "destructive_action_audits": {
        "id",
        "store_id",
        "user_id",
        "user_role",
        "event_type",
        "entity_type",
        "entity_id",
        "reference",
        "original_status",
        "final_action",
        "record_counts",
        "reversal_ids",
        "request_id",
        "client_ip",
        "created_at",
    },
    "destructive_idempotency_records": {
        "id",
        "store_id",
        "user_id",
        "action",
        "idempotency_key",
        "request_hash",
        "response_snapshot",
        "created_at",
    },
}

_REPAIR_MARKER = "created by 20260825_0045 destructive-action schema repair"

_REQUIRED_INDEXES = {
    "delete_password_attempts": {
        "ix_delete_password_attempts_store_id",
        "ix_delete_password_attempts_user_id",
        "ix_delete_password_attempts_attempted_at",
    },
    "destructive_action_audits": {
        "ix_destructive_action_audits_store_id",
        "ix_destructive_action_audits_user_id",
        "ix_destructive_action_audits_event_type",
        "ix_destructive_action_audits_entity_id",
        "ix_destructive_action_audits_request_id",
    },
    "destructive_idempotency_records": {"uq_destructive_idempotency"},
}


def _assert_existing_tables_are_complete() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    for table, required_columns in _REQUIRED_COLUMNS.items():
        if table not in tables:
            continue
        actual_columns = {column["name"] for column in inspector.get_columns(table)}
        missing = sorted(required_columns - actual_columns)
        if missing:
            raise RuntimeError(
                f"Refusing to repair partially-created {table}; missing columns: {', '.join(missing)}"
            )
        actual_indexes = {index["name"] for index in inspector.get_indexes(table)}
        actual_unique = {constraint["name"] for constraint in inspector.get_unique_constraints(table)}
        missing_indexes = sorted(_REQUIRED_INDEXES.get(table, set()) - actual_indexes - actual_unique)
        if missing_indexes:
            raise RuntimeError(
                f"Refusing to repair partially-created {table}; missing indexes or constraints: {', '.join(missing_indexes)}"
            )
    return tables


def upgrade() -> None:
    tables = _assert_existing_tables_are_complete()
    uuid = postgresql.UUID(as_uuid=True)

    if "store_security_settings" not in tables:
        op.create_table(
            "store_security_settings",
            sa.Column("store_id", uuid, sa.ForeignKey("stores.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("delete_password_hash", sa.String()),
            sa.Column("require_password_for_sale_delete", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("require_password_for_purchase_delete", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("updated_by", uuid, sa.ForeignKey("users.id", ondelete="SET NULL")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        op.execute("COMMENT ON TABLE store_security_settings IS 'created by 20260825_0045 destructive-action schema repair'")

    if "delete_password_attempts" not in tables:
        op.create_table(
            "delete_password_attempts",
            sa.Column("id", uuid, primary_key=True),
            sa.Column("store_id", uuid, sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        op.create_index("ix_delete_password_attempts_store_id", "delete_password_attempts", ["store_id"])
        op.create_index("ix_delete_password_attempts_user_id", "delete_password_attempts", ["user_id"])
        op.create_index("ix_delete_password_attempts_attempted_at", "delete_password_attempts", ["attempted_at"])
        op.execute("COMMENT ON TABLE delete_password_attempts IS 'created by 20260825_0045 destructive-action schema repair'")

    if "destructive_action_audits" not in tables:
        op.create_table(
            "destructive_action_audits",
            sa.Column("id", uuid, primary_key=True),
            sa.Column("store_id", uuid, sa.ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="SET NULL")),
            sa.Column("user_role", sa.String(32)),
            sa.Column("event_type", sa.String(80), nullable=False),
            sa.Column("entity_type", sa.String(32)),
            sa.Column("entity_id", uuid),
            sa.Column("reference", sa.String(180)),
            sa.Column("original_status", sa.String(40)),
            sa.Column("final_action", sa.String(40)),
            sa.Column("record_counts", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
            sa.Column("reversal_ids", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
            sa.Column("request_id", sa.String(80), nullable=False),
            sa.Column("client_ip", sa.String(64)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        )
        for name, columns in (
            ("ix_destructive_action_audits_store_id", ["store_id"]),
            ("ix_destructive_action_audits_user_id", ["user_id"]),
            ("ix_destructive_action_audits_event_type", ["event_type"]),
            ("ix_destructive_action_audits_entity_id", ["entity_id"]),
            ("ix_destructive_action_audits_request_id", ["request_id"]),
        ):
            op.create_index(name, "destructive_action_audits", columns)
        op.execute("COMMENT ON TABLE destructive_action_audits IS 'created by 20260825_0045 destructive-action schema repair'")

    if "destructive_idempotency_records" not in tables:
        op.create_table(
            "destructive_idempotency_records",
            sa.Column("id", uuid, primary_key=True),
            sa.Column("store_id", uuid, sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", uuid, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("action", sa.String(40), nullable=False),
            sa.Column("idempotency_key", sa.String(120), nullable=False),
            sa.Column("request_hash", sa.String(64), nullable=False),
            sa.Column("response_snapshot", postgresql.JSONB(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
            sa.UniqueConstraint("store_id", "user_id", "action", "idempotency_key", name="uq_destructive_idempotency"),
        )
        op.execute("COMMENT ON TABLE destructive_idempotency_records IS 'created by 20260825_0045 destructive-action schema repair'")


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    # Only remove tables marked by this migration.  Tables that predate this
    # repair are retained even if empty.
    def created_by_this_repair(table: str) -> bool:
        return op.get_bind().execute(
            sa.text("SELECT obj_description(to_regclass(:table), 'pg_class')"), {"table": table}
        ).scalar_one_or_none() == _REPAIR_MARKER

    if "destructive_idempotency_records" in tables and created_by_this_repair("destructive_idempotency_records"):
        record_count = op.get_bind().execute(sa.text("SELECT count(*) FROM destructive_idempotency_records")).scalar_one()
        if record_count:
            raise RuntimeError("Refusing to downgrade destructive_idempotency_records with retained audit evidence")
        op.drop_table("destructive_idempotency_records")
    if "destructive_action_audits" in tables and created_by_this_repair("destructive_action_audits"):
        record_count = op.get_bind().execute(sa.text("SELECT count(*) FROM destructive_action_audits")).scalar_one()
        if record_count:
            raise RuntimeError("Refusing to downgrade destructive_action_audits with retained audit evidence")
        op.drop_table("destructive_action_audits")
    if "delete_password_attempts" in tables and created_by_this_repair("delete_password_attempts"):
        record_count = op.get_bind().execute(sa.text("SELECT count(*) FROM delete_password_attempts")).scalar_one()
        if record_count:
            raise RuntimeError("Refusing to downgrade delete_password_attempts with retained security evidence")
        op.drop_table("delete_password_attempts")
    if "store_security_settings" in tables and created_by_this_repair("store_security_settings"):
        record_count = op.get_bind().execute(sa.text("SELECT count(*) FROM store_security_settings")).scalar_one()
        if record_count:
            raise RuntimeError("Refusing to downgrade store_security_settings with retained security settings")
        op.drop_table("store_security_settings")
