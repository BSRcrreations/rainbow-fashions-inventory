"""Read-only Alembic/ORM schema verification for disposable or review databases."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app import models  # noqa: F401
from app.database.base import Base


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify one Alembic head and ORM table/column coverage")
    parser.add_argument("--database-url", help="Disposable or explicitly selected database URL; verification is read-only")
    args = parser.parse_args()
    config = Config(str(ROOT / "backend" / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "backend" / "alembic"))
    heads = ScriptDirectory.from_config(config).get_heads()
    result: dict[str, object] = {"alembic_heads": list(heads), "single_head": len(heads) == 1}
    if args.database_url:
        engine = create_engine(args.database_url, pool_pre_ping=True)
        try:
            inspector = inspect(engine)
            database_tables = set(inspector.get_table_names())
            metadata_tables = set(Base.metadata.tables)
            missing_tables = sorted(metadata_tables - database_tables)
            missing_columns: dict[str, list[str]] = {}
            for table in sorted(metadata_tables & database_tables):
                actual = {column["name"] for column in inspector.get_columns(table)}
                expected = {column.name for column in Base.metadata.tables[table].columns}
                if expected - actual:
                    missing_columns[table] = sorted(expected - actual)
            result.update({"metadata_tables": len(metadata_tables), "database_tables": len(database_tables), "missing_tables": missing_tables, "missing_columns": missing_columns, "schema_compatible": not missing_tables and not missing_columns})
        finally:
            engine.dispose()
    print(json.dumps(result, sort_keys=True))
    return 0 if result["single_head"] and result.get("schema_compatible", True) else 1


if __name__ == "__main__":
    sys.exit(main())
