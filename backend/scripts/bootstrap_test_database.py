from __future__ import annotations

from pathlib import Path
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import models  # noqa: F401
from app.core.config import get_settings
from app.core.testing import assert_test_database
from app.database.base import Base


def main() -> None:
    settings = get_settings()
    database_name = assert_test_database(settings.app_env, settings.database_url)
    engine = create_engine(settings.database_url)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names(schema="public"))
    if "alembic_version" in tables:
        print(f"Testing database {database_name} already has Alembic metadata.")
        return
    if tables:
        raise SystemExit(
            f"Refusing to stamp partially initialized database {database_name}; "
            "drop the isolated test schema first."
        )

    Base.metadata.create_all(engine)
    alembic_cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    command.stamp(alembic_cfg, "head")
    print(f"Bootstrapped empty testing database {database_name} from current models and stamped Alembic head.")


if __name__ == "__main__":
    main()
