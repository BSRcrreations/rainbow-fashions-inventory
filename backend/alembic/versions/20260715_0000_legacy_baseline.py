"""Create the original empty schema so the complete migration chain is replayable.

Frozen DDL from the initial repository schema; no application models or seeds.
Existing databases already stamped at a later revision do not run this step.
"""
from pathlib import Path

from alembic import op
import sqlalchemy as sa

revision = "20260715_0000"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names()) - {"alembic_version"}
    if tables:
        raise RuntimeError("An unversioned database already contains tables. Review its migration revision before upgrading; no records were changed.")
    ddl = Path(__file__).resolve().parents[1] / "sql" / "20260715_legacy_baseline.sql"
    op.get_bind().exec_driver_sql(ddl.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise RuntimeError("The baseline cannot be downgraded. Restore a verified backup into an isolated database instead.")
