"""Repair missing store purge-guard schema on databases stamped through 0045.

Revision ID: 20260825_0046
Revises: 20260825_0045
Create Date: 2026-08-25

The original 20260728_0014 migration added the store purge guard and product
deletion audit evidence.  Legacy production drift left both objects absent
while recording later Alembic revisions.  This repair is additive and refuses
partially-created structures.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260825_0046"
down_revision = "20260825_0045"
branch_labels = None
depends_on = None


_TABLE = "product_deletion_audits"
_COLUMN = "allow_test_data_purge"
_MARKER = "created by 20260825_0046 store purge-schema repair"
_REQUIRED_COLUMNS = {
    "id",
    "store_id",
    "product_id",
    "event_type",
    "delete_mode",
    "reason",
    "request_id",
    "product_snapshot",
    "deleted_record_counts",
    "performed_by",
    "performed_by_role",
    "created_at",
}
_REQUIRED_INDEXES = {
    "ix_product_deletion_audits_store_id",
    "ix_product_deletion_audits_product_id",
    "ix_product_deletion_audits_event_type",
    "ix_product_deletion_audits_request_id",
    "ix_product_deletion_audits_created_at",
}


def _assert_existing_audit_is_complete(inspector: sa.Inspector) -> None:
    if _TABLE not in set(inspector.get_table_names()):
        return
    columns = {column["name"] for column in inspector.get_columns(_TABLE)}
    missing_columns = sorted(_REQUIRED_COLUMNS - columns)
    if missing_columns:
        raise RuntimeError(
            "Refusing to repair partially-created product_deletion_audits; missing columns: "
            + ", ".join(missing_columns)
        )
    indexes = {index["name"] for index in inspector.get_indexes(_TABLE)}
    missing_indexes = sorted(_REQUIRED_INDEXES - indexes)
    if missing_indexes:
        raise RuntimeError(
            "Refusing to repair partially-created product_deletion_audits; missing indexes: "
            + ", ".join(missing_indexes)
        )


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    store_columns = {column["name"]: column for column in inspector.get_columns("stores")}
    if _COLUMN in store_columns:
        if not isinstance(store_columns[_COLUMN]["type"], sa.Boolean):
            raise RuntimeError("Refusing to repair stores.allow_test_data_purge with a non-boolean type")
    else:
        op.add_column("stores", sa.Column(_COLUMN, sa.Boolean(), server_default=sa.false(), nullable=False))
        op.execute("COMMENT ON COLUMN stores.allow_test_data_purge IS 'created by 20260825_0046 store purge-schema repair'")

    _assert_existing_audit_is_complete(inspector)
    if _TABLE in set(inspector.get_table_names()):
        return

    uuid = postgresql.UUID(as_uuid=True)
    op.create_table(
        _TABLE,
        sa.Column("id", uuid, primary_key=True),
        sa.Column("store_id", uuid, sa.ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("product_id", uuid, nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("delete_mode", sa.String(40), nullable=False),
        sa.Column("reason", sa.String(500)),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("product_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("deleted_record_counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("performed_by", uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("performed_by_role", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    for name, columns in (
        ("ix_product_deletion_audits_store_id", ["store_id"]),
        ("ix_product_deletion_audits_product_id", ["product_id"]),
        ("ix_product_deletion_audits_event_type", ["event_type"]),
        ("ix_product_deletion_audits_request_id", ["request_id"]),
        ("ix_product_deletion_audits_created_at", ["created_at"]),
    ):
        op.create_index(name, _TABLE, columns)
    op.execute("COMMENT ON TABLE product_deletion_audits IS 'created by 20260825_0046 store purge-schema repair'")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _TABLE in set(inspector.get_table_names()):
        marked_table = bind.execute(
            sa.text("SELECT obj_description(to_regclass(:table), 'pg_class')"), {"table": _TABLE}
        ).scalar_one_or_none() == _MARKER
        if marked_table:
            count = bind.execute(sa.text("SELECT count(*) FROM product_deletion_audits")).scalar_one()
            if count:
                raise RuntimeError("Refusing to downgrade product_deletion_audits with retained audit evidence")
            op.drop_table(_TABLE)
    store_columns = {column["name"] for column in inspector.get_columns("stores")}
    if _COLUMN in store_columns:
        marked_column = bind.execute(
            sa.text("SELECT col_description('stores'::regclass, attnum) FROM pg_attribute WHERE attrelid='stores'::regclass AND attname=:column"),
            {"column": _COLUMN},
        ).scalar_one_or_none() == _MARKER
        if marked_column:
            op.drop_column("stores", _COLUMN)
