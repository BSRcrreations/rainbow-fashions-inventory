"""Clear residual cost-lot balances from completed opening-stock reversals."""

from alembic import op


revision = "20260924_0054"
down_revision = "20260910_0053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE inventory_cost_lots AS lot
        SET remaining_quantity = 0
        FROM opening_stock_import_rows AS row,
             opening_stock_imports AS batch
        WHERE row.cost_lot_id = lot.id
          AND row.opening_stock_import_id = batch.id
          AND batch.status = 'REVERSED'
          AND lot.remaining_quantity <> 0
        """
    )


def downgrade() -> None:
    raise RuntimeError("Do not restore cost-lot balances for reversed opening stock.")
