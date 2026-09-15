"""Record receipt tax details at the time of sale; retain historical bills."""
from alembic import op
import sqlalchemy as sa
revision = "20260910_0052"
down_revision = "20260909_0051"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("sale_items", sa.Column("hsn_snapshot", sa.String(40)))
    op.add_column("sale_items", sa.Column("gst_rate_snapshot", sa.Numeric(5, 2)))
    for name in ("taxable_value", "cgst_amount", "sgst_amount", "igst_amount"):
        op.add_column("sale_items", sa.Column(name, sa.Numeric(12, 2), nullable=False, server_default="0"))


def downgrade():
    raise RuntimeError("Do not remove receipt evidence. Roll back the application while retaining the schema.")
