#!/usr/bin/env bash
# Weekly non-production restore drill. Never run against production: this script
# requires explicit staging markers and a database name ending in _restore_test.
set -Eeuo pipefail
CONFIG_FILE="${BACKUP_CONFIG_FILE:-/etc/rainbow-fashions/backup.env}"
[[ -r "$CONFIG_FILE" ]] || { echo "Missing protected backup configuration: $CONFIG_FILE" >&2; exit 2; }
source "$CONFIG_FILE"
: "${BACKUP_LOCAL_PATH:=/u02/backups}"
: "${RESTORE_TEST_ENVIRONMENT:?RESTORE_TEST_ENVIRONMENT=staging is required}"
: "${RESTORE_TEST_DB_HOST:?RESTORE_TEST_DB_HOST is required}"
: "${RESTORE_TEST_DB_PORT:=5432}"
: "${RESTORE_TEST_DB_NAME:?RESTORE_TEST_DB_NAME is required}"
: "${RESTORE_TEST_DB_USER:?RESTORE_TEST_DB_USER is required}"
[[ "$RESTORE_TEST_ENVIRONMENT" == staging ]] || { echo "Restore drills are permitted only in staging." >&2; exit 2; }
[[ "$RESTORE_TEST_DB_NAME" == *_restore_test ]] || { echo "Restore drill database must end in _restore_test." >&2; exit 2; }
[[ "$RESTORE_TEST_DB_HOST" != *prod* && "$RESTORE_TEST_DB_HOST" != *production* ]] || { echo "Production-like hosts are forbidden for restore drills." >&2; exit 2; }

STATUS_DIR="$BACKUP_LOCAL_PATH/status"; mkdir -p "$STATUS_DIR"; chmod 700 "$STATUS_DIR"; umask 077
LATEST="$(find "$BACKUP_LOCAL_PATH/database" -maxdepth 1 -type f -name 'rainbow_inventory_db_*.dump' -print | sort | tail -n 1)"
[[ -n "$LATEST" && -s "$LATEST" ]] || { echo "No database backup available for restore drill." >&2; exit 1; }
if command -v sha256sum >/dev/null; then (cd "$(dirname "$LATEST")" && sha256sum --check "$(basename "${LATEST}.sha256")") >/dev/null; else (cd "$(dirname "$LATEST")" && shasum -a 256 --check "$(basename "${LATEST}.sha256")") >/dev/null; fi
pg_restore --list "$LATEST" >/dev/null
START="$(date --iso-8601=seconds 2>/dev/null || date)"; RESULT=failed; COUNT=0
write_status() { printf '{"component":"restore_test","status":"%s","started_at":"%s","finished_at":"%s","backup_file":"%s","table_count":%s,"message":"%s"}\n' "$RESULT" "$START" "$(date --iso-8601=seconds 2>/dev/null || date)" "$(basename "$LATEST")" "$COUNT" "$1" > "$STATUS_DIR/latest-restore-test.json"; chmod 600 "$STATUS_DIR/latest-restore-test.json"; }
trap 'code=$?; write_status "Restore drill failed (exit ${code})."; exit "$code"' ERR
pg_restore --host="$RESTORE_TEST_DB_HOST" --port="$RESTORE_TEST_DB_PORT" --username="$RESTORE_TEST_DB_USER" --dbname="$RESTORE_TEST_DB_NAME" --clean --if-exists --no-owner --exit-on-error "$LATEST"
COUNT="$(psql --host="$RESTORE_TEST_DB_HOST" --port="$RESTORE_TEST_DB_PORT" --username="$RESTORE_TEST_DB_USER" --dbname="$RESTORE_TEST_DB_NAME" --tuples-only --no-align --command "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")"
[[ "$COUNT" =~ ^[1-9][0-9]*$ ]] || { echo "Restored database has no public tables" >&2; exit 1; }
RESULT=success; write_status "Restore drill passed; restored ${COUNT} public tables into staging-only target."
