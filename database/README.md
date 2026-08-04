# Database files

This directory is versioned with the application and contains database SQL that is safe to review in Git.

- `schema.sql` is a non-authoritative, legacy schema snapshot. Fresh databases are created with `alembic upgrade head`; Docker Compose does not load this file.
- `seed.sql` is an opt-in development/test fixture and is never run by production Docker Compose.
- `queries/inspect_tables.sql` reports the current local database tables, columns, constraints, and indexes without reading business data.
- `local-schema.sql` is the optional schema-only export created from a running local database. It contains no table rows or secrets and may be committed after review.

## Inspect a local database

Run the metadata queries against a configured local PostgreSQL instance:

```bash
psql "${DATABASE_URL}" -f database/queries/inspect_tables.sql
```

For the project migration configuration, first create the ignored local configuration file:

```bash
cp scripts/database/database-migration.env.example scripts/database/database-migration.env
```

Set its `LOCAL_DATABASE_*` values, then export only the local database DDL:

```bash
scripts/database/export_local_schema.sh
```

The export is written to `database/local-schema.sql`. To use another destination, set `DATABASE_SCHEMA_EXPORT_FILE` before running the command.

Regenerate a review-only local snapshot with `scripts/database/export_local_schema.sh`; it must not be used to initialize an application database.

Never commit database dumps (`*.dump`, `*.backup`), local environment files, or production data.
