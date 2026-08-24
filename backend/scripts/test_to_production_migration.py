#!/usr/bin/env python3
"""Controlled TEST-to-production catalog migration command.

Default operation is a read-only dry run.  ``execute`` is deliberately guarded
and is not used by CI or deployment jobs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from uuid import UUID

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.services.test_to_production_migration_service import (
    CATALOG_AND_OPENING_STOCK,
    CATALOG_ONLY,
    MigrationSafetyError,
    TestToProductionMigrationService,
)


def _database_name(url: str) -> str:
    return url.rsplit("/", 1)[-1].split("?", 1)[0]


def _session(url: str) -> Session:
    return Session(create_engine(url, pool_pre_ping=True))


def export(args: argparse.Namespace) -> int:
    approved = TestToProductionMigrationService.read_approved_stock(args.approved_stock) if args.mode == CATALOG_AND_OPENING_STOCK else None
    if _database_name(args.source_database_url) != "rainbow_test_db":
        raise MigrationSafetyError("--source-database-url must point to rainbow_test_db.")
    with _session(args.source_database_url) as db:
        package = TestToProductionMigrationService(db).export_package(source_store_code=args.source_store_code, source_database="rainbow_test_db", source_git_sha=args.source_sha, mode=args.mode, approved_stock=approved)
    path = TestToProductionMigrationService.write_package(package, args.output_dir)
    print(json.dumps({"package_id": package["package_id"], "package_dir": str(path), "counts": package["counts"]}, indent=2, sort_keys=True))
    return 0


def dry_run(args: argparse.Namespace) -> int:
    package = TestToProductionMigrationService.read_package(args.package_dir)
    if _database_name(args.target_database_url) != "inventory_db":
        raise MigrationSafetyError("--target-database-url must point to inventory_db.")
    with _session(args.target_database_url) as db:
        actual_db = db.execute(text("select current_database()")).scalar_one()
        if actual_db != "inventory_db":
            raise MigrationSafetyError("Connected database is not inventory_db.")
        report = TestToProductionMigrationService(db).dry_run(package, target_store_code=args.target_store_code)
    print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    return 1 if report.conflicts else 0


def execute(args: argparse.Namespace) -> int:
    package = TestToProductionMigrationService.read_package(args.package_dir)
    if _database_name(args.target_database_url) != "inventory_db":
        raise MigrationSafetyError("--target-database-url must point to inventory_db.")
    try:
        gates = json.loads(args.gate_evidence.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationSafetyError("Gate evidence must be a readable JSON file.") from exc
    # These are intentionally read from the execution environment rather than
    # trusted from a command-line flag.  A production run must be launched in
    # the verified Compose context itself.
    compose_project = os.environ.get("COMPOSE_PROJECT_NAME", "")
    postgres_volume = os.environ.get("POSTGRES_DATA_VOLUME", "")
    with _session(args.target_database_url) as db:
        actual_db = db.execute(text("select current_database()")).scalar_one()
        # ``execute`` owns one atomic transaction.  End this identity-only
        # read transaction before handing the session to the service.
        db.rollback()
        report = TestToProductionMigrationService(db).execute(package, target_store_code=args.target_store_code, executing_user_id=UUID(args.executing_user_id), owner_authorization=args.owner_authorization, target_database=actual_db, compose_project=compose_project, postgres_volume=postgres_volume, gate_evidence=gates)
    print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    return 0


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(prog="test_to_production_migration")
    commands = command.add_subparsers(dest="command", required=True)
    export_parser = commands.add_parser("export", help="Create a secret-free package from rainbow_test_db")
    export_parser.add_argument("--source-database-url", required=True)
    export_parser.add_argument("--source-store-code", required=True)
    export_parser.add_argument("--source-sha", required=True)
    export_parser.add_argument("--mode", choices=(CATALOG_ONLY, CATALOG_AND_OPENING_STOCK), default=CATALOG_ONLY)
    export_parser.add_argument("--approved-stock", type=Path, help="Required only for CATALOG_AND_OPENING_STOCK")
    export_parser.add_argument("--output-dir", type=Path, required=True)
    export_parser.set_defaults(handler=export)
    dry_parser = commands.add_parser("dry-run", help="Read-only conflict report against inventory_db")
    dry_parser.add_argument("--package-dir", type=Path, required=True)
    dry_parser.add_argument("--target-database-url", required=True)
    dry_parser.add_argument("--target-store-code", required=True)
    dry_parser.set_defaults(handler=dry_run)
    execute_parser = commands.add_parser("execute", help="Guarded production apply; never the default")
    execute_parser.add_argument("--package-dir", type=Path, required=True)
    execute_parser.add_argument("--target-database-url", required=True)
    execute_parser.add_argument("--target-store-code", required=True)
    execute_parser.add_argument("--executing-user-id", required=True)
    execute_parser.add_argument("--gate-evidence", type=Path, required=True)
    execute_parser.add_argument("--owner-authorization")
    execute_parser.set_defaults(handler=execute)
    return command


def main() -> int:
    args = parser().parse_args()
    if args.command == "export" and args.mode == CATALOG_AND_OPENING_STOCK and not args.approved_stock:
        raise SystemExit("--approved-stock is required for CATALOG_AND_OPENING_STOCK")
    try:
        return args.handler(args)
    except MigrationSafetyError as exc:
        print(f"migration safety check failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
