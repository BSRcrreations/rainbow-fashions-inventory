from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


revision = "20260803_0037"
down_revision = "20260803_0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    supplier_columns = {column["name"] for column in inspector.get_columns("suppliers")}
    supplier_column_sql = {
        "store_id": "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS store_id UUID REFERENCES stores(id) ON DELETE CASCADE",
        "contact_person": "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS contact_person VARCHAR(140)",
        "alternate_phone": "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS alternate_phone VARCHAR(30)",
        "pan_number": "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS pan_number VARCHAR(40)",
        "city": "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS city VARCHAR(120)",
        "state": "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS state VARCHAR(120)",
        "postal_code": "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS postal_code VARCHAR(20)",
        "opening_balance": "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS opening_balance NUMERIC(12, 2) NOT NULL DEFAULT 0",
        "credit_limit": "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS credit_limit NUMERIC(12, 2)",
        "notes": "ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS notes TEXT",
    }
    for column_name, statement in supplier_column_sql.items():
        if column_name not in supplier_columns:
            op.execute(statement)
    op.execute("CREATE INDEX IF NOT EXISTS ix_suppliers_store_id ON suppliers (store_id)")

    if not inspector.has_table("customers"):
        op.create_table(
            "customers",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
            sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(length=180), nullable=False),
            sa.Column("phone", sa.String(length=30), nullable=True),
            sa.Column("alternate_phone", sa.String(length=30), nullable=True),
            sa.Column("email", sa.String(length=255), nullable=True),
            sa.Column("gst_number", sa.String(length=40), nullable=True),
            sa.Column("address", sa.Text(), nullable=True),
            sa.Column("city", sa.String(length=120), nullable=True),
            sa.Column("state", sa.String(length=120), nullable=True),
            sa.Column("postal_code", sa.String(length=20), nullable=True),
            sa.Column("opening_credit", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("credit_limit", sa.Numeric(12, 2), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("store_id", "phone", name="uq_customers_store_phone"),
        )
    op.execute("CREATE INDEX IF NOT EXISTS ix_customers_store_id ON customers (store_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_customers_name ON customers (name)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_customers_phone ON customers (phone)")

    if "customer_id" not in {column["name"] for column in inspector.get_columns("sales")}:
        op.execute("ALTER TABLE sales ADD COLUMN IF NOT EXISTS customer_id UUID REFERENCES customers(id) ON DELETE SET NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_sales_customer_id ON sales (customer_id)")

    if not inspector.has_table("supplier_payments"):
        op.create_table(
        "supplier_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payment_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_mode", sa.String(length=40), nullable=False),
        sa.Column("reference", sa.String(length=140), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    op.execute("CREATE INDEX IF NOT EXISTS ix_supplier_payments_store_id ON supplier_payments (store_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_supplier_payments_supplier_id ON supplier_payments (supplier_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_supplier_payments_payment_date ON supplier_payments (payment_date)")

    if not inspector.has_table("customer_payments"):
        op.create_table(
        "customer_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payment_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_mode", sa.String(length=40), nullable=False),
        sa.Column("reference", sa.String(length=140), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    op.execute("CREATE INDEX IF NOT EXISTS ix_customer_payments_store_id ON customer_payments (store_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_customer_payments_customer_id ON customer_payments (customer_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_customer_payments_payment_date ON customer_payments (payment_date)")

    if not inspector.has_table("expense_categories"):
        op.create_table(
        "expense_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("store_id", "name", name="uq_expense_categories_store_name"),
        )
    op.execute("CREATE INDEX IF NOT EXISTS ix_expense_categories_store_id ON expense_categories (store_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_expense_categories_name ON expense_categories (name)")

    if not inspector.has_table("expenses"):
        op.create_table(
        "expenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("store_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stores.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("expense_categories.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("vendor", sa.String(length=180), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_mode", sa.String(length=40), nullable=False),
        sa.Column("reference", sa.String(length=140), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("receipt_url", sa.String(length=500), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    op.execute("CREATE INDEX IF NOT EXISTS ix_expenses_store_id ON expenses (store_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_expenses_category_id ON expenses (category_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_expenses_expense_date ON expenses (expense_date)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_expenses_vendor ON expenses (vendor)")


def downgrade() -> None:
    op.drop_index("ix_expenses_vendor", table_name="expenses")
    op.drop_index("ix_expenses_expense_date", table_name="expenses")
    op.drop_index("ix_expenses_category_id", table_name="expenses")
    op.drop_index("ix_expenses_store_id", table_name="expenses")
    op.drop_table("expenses")
    op.drop_index("ix_expense_categories_name", table_name="expense_categories")
    op.drop_index("ix_expense_categories_store_id", table_name="expense_categories")
    op.drop_table("expense_categories")
    op.drop_index("ix_customer_payments_payment_date", table_name="customer_payments")
    op.drop_index("ix_customer_payments_customer_id", table_name="customer_payments")
    op.drop_index("ix_customer_payments_store_id", table_name="customer_payments")
    op.drop_table("customer_payments")
    op.drop_index("ix_supplier_payments_payment_date", table_name="supplier_payments")
    op.drop_index("ix_supplier_payments_supplier_id", table_name="supplier_payments")
    op.drop_index("ix_supplier_payments_store_id", table_name="supplier_payments")
    op.drop_table("supplier_payments")
    op.drop_index("ix_sales_customer_id", table_name="sales")
    op.drop_column("sales", "customer_id")
    op.drop_index("ix_customers_phone", table_name="customers")
    op.drop_index("ix_customers_name", table_name="customers")
    op.drop_index("ix_customers_store_id", table_name="customers")
    op.drop_table("customers")
    op.drop_index("ix_suppliers_store_id", table_name="suppliers")
    for column in ("notes", "credit_limit", "opening_balance", "postal_code", "state", "city", "pan_number", "alternate_phone", "contact_person", "store_id"):
        op.drop_column("suppliers", column)
