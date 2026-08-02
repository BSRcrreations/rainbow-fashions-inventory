#!/usr/bin/env bash
# Clear production business data after creating a local PostgreSQL backup.
# This script is intentionally usable only from the explicit GitLab manual job.
set -Eeuo pipefail

APP_DIR="${DEPLOY_PATH:-/opt/rainbow-fashions}"
CURRENT_RELEASE="$APP_DIR/current"
BACKUP_DIR="$APP_DIR/backups/data-reset"
CONFIRMATION="${1:-}"

if [[ "$CONFIRMATION" != "--confirm-clear-production-data" ]]; then
  printf '%s\n' 'Refusing to clear production data without --confirm-clear-production-data.' >&2
  exit 1
fi

[[ -d "$CURRENT_RELEASE" ]] || { printf '%s\n' "Current release is missing: $CURRENT_RELEASE" >&2; exit 1; }
[[ -s "$CURRENT_RELEASE/backend/.env" ]] || { printf '%s\n' 'Production backend environment is missing.' >&2; exit 1; }

mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_file="$BACKUP_DIR/pre_reset_${timestamp}.dump"
cd "$CURRENT_RELEASE"

# Docker Compose obtains the connection values from backend/.env. The backup
# remains on the production host with restricted permissions and is never sent
# to CI logs or artifacts.
docker compose exec -T postgres sh -ec 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > "$backup_file"
[[ -s "$backup_file" ]] || { printf '%s\n' 'Production backup is empty; refusing to clear data.' >&2; exit 1; }
chmod 600 "$backup_file"

# Keep only authentication, store configuration, and Alembic migration state.
# All other public application tables are emptied, including catalog, stock,
# sales, purchases, barcodes, audit rows, documents, and customer data.
docker compose exec -T postgres sh -ec 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
DO $$
DECLARE
  target_tables text;
BEGIN
  SELECT string_agg(format('%I.%I', schemaname, tablename), ', ' ORDER BY tablename)
    INTO target_tables
  FROM pg_tables
  WHERE schemaname = 'public'
    AND tablename NOT IN ('alembic_version', 'stores', 'users');

  IF target_tables IS NOT NULL THEN
    EXECUTE 'TRUNCATE TABLE ' || target_tables || ' RESTART IDENTITY CASCADE';
  END IF;
END
$$;
SQL

# Uploaded product, purchase, and invoice files are operational data too.
# The directory itself is retained so the backend can continue writing files.
docker compose exec -T backend sh -ec '
  set -eu
  upload_dir=/app/app/uploads
  if [ -d "$upload_dir" ]; then
    find "$upload_dir" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
  fi
'

remaining="$(docker compose exec -T postgres sh -ec 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT count(*) FROM products"')"
[[ "$remaining" == "0" ]] || { printf '%s\n' 'Product records remain after the reset.' >&2; exit 1; }

printf '%s\n' "Production business data cleared. Backup retained at $backup_file"
