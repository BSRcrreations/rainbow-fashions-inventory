# Production Database Migration

This runbook moves a checked local PostgreSQL database into the Contabo production database without placing dumps, passwords, private keys, or backups in Git.

The scripts use PostgreSQL custom-format dumps (`pg_dump -Fc`) and restore with `--no-owner --no-acl`. They are intentionally parameterized: do not infer remote container names, database names, users, directories, or SSH details from a different environment.

## Safety Rules

- Do not run an import until the production backup command has completed, produced a non-empty file, and produced a SHA-256 checksum.
- `import_remote_database.sh` makes a new production backup itself before opening its destructive confirmation gate.
- Only run an import during an approved maintenance window. It stops the production backend while restoring.
- Keep the printed rollback path. It is required by the rollback command.
- Never add `database-migration.env`, `*.dump`, `*.backup`, `database-migration-artifacts/`, `.env`, SSH keys, or generated backups to Git.
- Product images and invoice documents are stored outside PostgreSQL by this application. Database migration alone does not copy those files.

## One-Time Configuration

1. Copy the template locally:

   ```bash
   cd "/Users/subbu/Documents/shop inventory"
   cp scripts/database/database-migration.env.example scripts/database/database-migration.env
   chmod 600 scripts/database/database-migration.env
   ```

2. Set the values in `scripts/database/database-migration.env` using a local password manager, SSH configuration, Docker secrets, or environment variables. Do not send the file or any password in chat.

3. Set `LOCAL_DATABASE_MODE` to `direct` for a local PostgreSQL installation or `docker` for Docker Compose. For direct mode, `LOCAL_DATABASE_URL` must be a PostgreSQL CLI URL beginning with `postgresql://`; SQLAlchemy's `postgresql+psycopg://` form is normalized by the scripts.

4. Set the real remote SSH user, remote Compose directory, PostgreSQL service, backend service, database name, database user, backup directory, staging directory, and the exact staged dump path. The remote directory values must be writable by the SSH user and should not contain spaces.

5. Set `ALLOW_BACKEND_DOWNTIME=true` only after the maintenance window is approved.

6. Verify both environments before exporting:

   ```bash
   scripts/database/check_database_environment.sh
   ```

The check verifies that the `pg_dump` client is not older than its source PostgreSQL server. The remote check also reports the server's `pg_restore` version. Use a PostgreSQL client at least as new as the source server. A newer restore client can restore a dump from an older source server.

## Normal Import Workflow

1. Export the local database. The output includes the dump path and SHA-256 checksum.

   ```bash
   scripts/database/export_local_database.sh
   ```

2. Upload that exact dump. The script validates the custom dump and compares the remote SHA-256 checksum with the local value.

   ```bash
   scripts/database/upload_database_dump.sh database-migration-artifacts/rainbow_local_<timestamp>.dump
   ```

3. Optionally make and review a production backup before scheduling the change:

   ```bash
   scripts/database/backup_remote_database.sh
   ```

   Confirm the returned `REMOTE_BACKUP_PATH` exists, is non-empty, and has the returned checksum. The import performs this backup again immediately before the destructive confirmation, which prevents an old backup from being reused accidentally.

4. Review the rollback section below, notify users, and stop write activity. Run the import with the required command-line gate. In an interactive terminal, type `REPLACE_PRODUCTION_DATABASE` when prompted.

   ```bash
   scripts/database/import_remote_database.sh --confirm-replace
   ```

   In a non-interactive job, set the protected/masked variable `MIGRATION_IMPORT_CONFIRMATION=REPLACE_PRODUCTION_DATABASE`. The import refuses to proceed without it.

5. The script validates the staged dump, stops the backend, restores with `pg_restore --clean --if-exists --no-owner --no-acl`, runs `alembic upgrade heads`, restarts the backend, and runs database/service verification. It does not run from a normal Git push.

6. Perform manual verification: sign in, inspect category/product/brand counts, open a product image and invoice document, confirm stock totals, and create no test transaction until the import is accepted.

## Rollback

If validation fails after an import, restore the `REMOTE_BACKUP_PATH` printed by that import. First roll the application code back to a release compatible with the backup schema when required. The rollback script creates a new backup of the current state before restoring the requested backup.

```bash
scripts/database/rollback_remote_database.sh --confirm-rollback /absolute/remote/path/rainbow_production_before_import_<timestamp>.dump
```

In an interactive terminal, type `ROLLBACK_PRODUCTION_DATABASE`. In a protected non-interactive job, use `MIGRATION_ROLLBACK_CONFIRMATION=ROLLBACK_PRODUCTION_DATABASE`.

## Optional Media Migration

This application stores product images and invoice documents under the backend upload storage and, in Compose, a backend upload volume. These files are not included in a PostgreSQL dump.

Before copying media, compare the local and remote upload locations, make a remote backup, and use a non-destructive transfer such as `rsync -a --ignore-existing`. Do not use `--delete` on production media. Verify a representative product image and invoice document after the database import. Media transfer is intentionally not automated by the database scripts because the actual local and remote storage locations have not been confirmed.

## Protected GitLab Job

`database_import_production` is a manual-only job on the configured deployment branch. To enable it safely:

1. In GitLab, create and protect the `production-database-import` environment. Limit deployment approval to production operators.
2. Add `DATABASE_MIGRATION_ENV_FILE` as a protected **File** CI variable containing the migration configuration. Do not expose it in job logs.
3. Add `MIGRATION_IMPORT_CONFIRMATION` as a protected and masked CI variable with the exact required phrase only for the approved run.
4. Stage the dump first using the local upload script. The job reads the remote staged file; it does not receive dump artifacts from GitLab.
5. Start the manual job only after reviewing the backup and rollback plan.

## Individual Commands

| Script | Purpose |
| --- | --- |
| `check_database_environment.sh` | Detects configured local/remote database access and PostgreSQL version compatibility. |
| `export_local_database.sh` | Creates a local custom-format dump, validates it, and writes checksum/manifest files. |
| `backup_remote_database.sh` | Creates, validates, and checksums a remote production backup. |
| `upload_database_dump.sh` | Uploads and checksum-verifies a local dump on the remote staging directory. |
| `import_remote_database.sh` | Backup-first, confirmed replacement of the remote database. |
| `verify_database_import.sh` | Checks database connectivity, Alembic presence, backend service state, and optional health URL. |
| `rollback_remote_database.sh` | Backup-first, confirmed restoration of a remote backup. |
| `migrate_database.sh` | Runs `alembic upgrade heads` in the configured remote backend service. |
