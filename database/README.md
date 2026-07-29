# Database files

This directory is versioned with the application and contains database SQL that is safe to review in Git.

- `schema.sql` creates the development database schema used by Docker Compose.
- `seed.sql` creates non-production sample records.
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

Never commit database dumps (`*.dump`, `*.backup`), local environment files, or production data.
