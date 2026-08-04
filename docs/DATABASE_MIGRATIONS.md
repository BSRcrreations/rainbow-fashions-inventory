# Database migrations

Alembic migrations are the authoritative database schema history. `database/schema.sql` is a non-authoritative legacy snapshot and must not initialize an application database.

## Deployment flow

1. Start PostgreSQL with an empty data volume; it initializes PostgreSQL only.
2. The backend container entrypoint runs `alembic upgrade head` before Uvicorn starts. Any migration failure stops the container.
3. Backend readiness succeeds only after the migrated required tables can be queried.

The entrypoint never downgrades and never runs `database/seed.sql`. Sample users and catalog records are available only through explicit development/test fixture commands.

## Verification

Run `python scripts/database/verify_schema_consistency.py` to confirm one Alembic head. For a disposable migrated database, add `--database-url` to compare ORM table and column coverage without reading business rows. Run this after both a fresh `alembic upgrade head` and a representative legacy upgrade.

When a review snapshot is needed, run `scripts/database/export_local_schema.sh`. It is documentation only, not an initializer.
