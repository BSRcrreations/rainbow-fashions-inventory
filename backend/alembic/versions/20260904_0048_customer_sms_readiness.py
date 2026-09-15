"""Add customer lifecycle and SMS-suppression readiness fields.

This is deliberately customer-record-only: no SMS provider, campaign, or POS
checkout consent UI is introduced here.
"""

from alembic import op


revision = "20260904_0048"
down_revision = "20260901_0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS sms_opt_out BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS sms_opted_out_at TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS sms_suppression_reason VARCHAR(300)")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS last_sms_sent_at TIMESTAMP WITH TIME ZONE")
    op.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS last_purchase_at TIMESTAMP WITH TIME ZONE")
    op.execute("CREATE INDEX IF NOT EXISTS ix_customers_sms_opt_out ON customers (store_id, sms_opt_out)")


def downgrade() -> None:
    # Keep audit-related customer fields on rollback to avoid discarding consent
    # and suppression history.
    pass
