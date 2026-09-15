"""Optional per-size low-stock thresholds; null inherits the product setting."""
from alembic import op
import sqlalchemy as sa
revision = "20260910_0053"
down_revision = "20260910_0052"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("product_variants", sa.Column("minimum_stock", sa.Integer(), nullable=True))
    op.create_check_constraint("ck_variant_minimum_stock_nonnegative", "product_variants", "minimum_stock IS NULL OR minimum_stock >= 0")


def downgrade():
    raise RuntimeError("Retain configured thresholds when rolling back the application.")
