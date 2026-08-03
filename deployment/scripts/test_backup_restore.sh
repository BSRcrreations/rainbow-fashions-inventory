#!/usr/bin/env bash
# Weekly restore validation for staging only. It creates and drops a dedicated
# temporary database; production-like hosts and names are rejected before I/O.
set -Eeuo pipefail
CONFIG_FILE="${BACKUP_CONFIG_FILE:-/etc/rainbow-fashions/backup.env}"
[[ -r "$CONFIG_FILE" ]] || { echo "Missing protected backup configuration: $CONFIG_FILE" >&2; exit 2; }
source "$CONFIG_FILE"
: "${BACKUP_LOCAL_PATH:=/u02/backups}"
: "${RESTORE_TEST_ENVIRONMENT:?RESTORE_TEST_ENVIRONMENT=staging is required}"
: "${RESTORE_TEST_DB_HOST:?RESTORE_TEST_DB_HOST is required}"
: "${RESTORE_TEST_DB_PORT:=5432}"
: "${RESTORE_TEST_DB_USER:?RESTORE_TEST_DB_USER is required}"
: "${RESTORE_TEST_ADMIN_DB:=postgres}"
[[ "$RESTORE_TEST_ENVIRONMENT" == staging ]] || { echo "Restore tests run only in staging." >&2; exit 2; }
[[ "$RESTORE_TEST_DB_HOST" != *prod* && "$RESTORE_TEST_DB_HOST" != *production* && "$RESTORE_TEST_DB_HOST" != *rainbow-fashions.in* ]] || { echo "Production-like restore host rejected." >&2; exit 2; }

REPORT_DIR="$BACKUP_LOCAL_PATH/restore-tests"; STATUS_DIR="$BACKUP_LOCAL_PATH/status"; LOG_DIR="$BACKUP_LOCAL_PATH/logs"
mkdir -p "$REPORT_DIR" "$STATUS_DIR" "$LOG_DIR"; chmod 700 "$REPORT_DIR" "$STATUS_DIR" "$LOG_DIR"; umask 077
command -v flock >/dev/null || { echo "flock is required" >&2; exit 127; }
exec 9>"$BACKUP_LOCAL_PATH/.restore-test.lock"
flock -n 9 || { echo "A restore test is already running" >&2; exit 1; }
STARTED_AT="$(date --iso-8601=seconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S%z')"; RUN_ID="$(date '+%Y%m%d_%H%M%S')"; TEMP_DB="rainbow_restore_test_${RUN_ID}"
REPORT_FILE="$REPORT_DIR/restore-test_${RUN_ID}.json"; RUN_LOG="$REPORT_DIR/restore-test_${RUN_ID}.log"
DATABASE_BACKUP="$(find "$BACKUP_LOCAL_PATH/database" -maxdepth 1 -type f -name 'rainbow_inventory_db_*.dump' -print | sort | tail -n 1)"
UPLOAD_BACKUP="$(find "$BACKUP_LOCAL_PATH/uploads" -maxdepth 1 -type f -name 'rainbow_inventory_uploads_*.tar.gz' -print | sort | tail -n 1)"
RESULT=failed; CHECKSUM_VALID=false; DB_RESTORE=failed; UPLOAD_VALIDATION=failed; QUERIES=failed; ERROR_MESSAGE=""; TEMP_CREATED=false
log() { printf '%s restore-test %s\n' "$(date --iso-8601=seconds 2>/dev/null || date)" "$*" | tee -a "$RUN_LOG" >&2; }
write_report() {
  local error_json=null
  [[ -n "$ERROR_MESSAGE" ]] && error_json="\"${ERROR_MESSAGE//\"/\\\"}\""
  printf '{"backup_file":"%s","uploads_file":"%s","started_at":"%s","completed_at":"%s","checksum_valid":%s,"database_restore":"%s","upload_archive_validation":"%s","validation_queries":"%s","result":"%s","error":%s}\n' \
    "$(basename "${DATABASE_BACKUP:-missing}")" "$(basename "${UPLOAD_BACKUP:-missing}")" "$STARTED_AT" "$(date --iso-8601=seconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S%z')" "$CHECKSUM_VALID" "$DB_RESTORE" "$UPLOAD_VALIDATION" "$QUERIES" "$RESULT" "$error_json" > "$REPORT_FILE"
  cp "$REPORT_FILE" "$STATUS_DIR/latest-restore-test.json"
  chmod 600 "$REPORT_FILE" "$STATUS_DIR/latest-restore-test.json"
}
cleanup() { [[ "$TEMP_CREATED" == true ]] && dropdb --host="$RESTORE_TEST_DB_HOST" --port="$RESTORE_TEST_DB_PORT" --username="$RESTORE_TEST_DB_USER" --if-exists "$TEMP_DB" >> "$RUN_LOG" 2>&1 || true; }
on_error() { code=$?; ERROR_MESSAGE="restore test failed (exit ${code}); see $(basename "$RUN_LOG")"; write_report; [[ -n "${BACKUP_ALERT_WEBHOOK_URL:-}" ]] && curl --fail --silent --max-time 15 -H 'Content-Type: application/json' --data "{\"service\":\"rainbow-fashions-backup\",\"severity\":\"failed\",\"message\":\"${ERROR_MESSAGE}\"}" "$BACKUP_ALERT_WEBHOOK_URL" || true; cleanup; exit "$code"; }
trap on_error ERR
trap cleanup EXIT
fail() { log "$1"; return 1; }

[[ -s "$DATABASE_BACKUP" && -s "$UPLOAD_BACKUP" ]] || fail "Database or uploads backup missing"
for archive in "$DATABASE_BACKUP" "$UPLOAD_BACKUP"; do
  [[ -s "${archive}.sha256" ]] || fail "Checksum missing for $archive"
  if command -v sha256sum >/dev/null; then (cd "$(dirname "$archive")" && sha256sum --check "$(basename "${archive}.sha256")") >> "$RUN_LOG" 2>&1; else (cd "$(dirname "$archive")" && shasum -a 256 --check "$(basename "${archive}.sha256")") >> "$RUN_LOG" 2>&1; fi
done
CHECKSUM_VALID=true
pg_restore --list "$DATABASE_BACKUP" >> "$RUN_LOG" 2>&1
tar --list --gzip --file="$UPLOAD_BACKUP" >> "$RUN_LOG" 2>&1
UPLOAD_VALIDATION=success

createdb --host="$RESTORE_TEST_DB_HOST" --port="$RESTORE_TEST_DB_PORT" --username="$RESTORE_TEST_DB_USER" --maintenance-db="$RESTORE_TEST_ADMIN_DB" "$TEMP_DB" >> "$RUN_LOG" 2>&1
TEMP_CREATED=true
pg_restore --host="$RESTORE_TEST_DB_HOST" --port="$RESTORE_TEST_DB_PORT" --username="$RESTORE_TEST_DB_USER" --dbname="$TEMP_DB" --no-owner --exit-on-error "$DATABASE_BACKUP" >> "$RUN_LOG" 2>&1
DB_RESTORE=success
for table in alembic_version products brands product_variants purchases sales users; do
  psql --host="$RESTORE_TEST_DB_HOST" --port="$RESTORE_TEST_DB_PORT" --username="$RESTORE_TEST_DB_USER" --dbname="$TEMP_DB" --tuples-only --no-align --command "SELECT to_regclass('public.${table}') IS NOT NULL;" | grep -qx t
done
psql --host="$RESTORE_TEST_DB_HOST" --port="$RESTORE_TEST_DB_PORT" --username="$RESTORE_TEST_DB_USER" --dbname="$TEMP_DB" --tuples-only --no-align --command "SELECT count(*) FROM products; SELECT count(*) FROM brands; SELECT coalesce(sum(current_stock), 0) FROM product_variants;" >> "$RUN_LOG" 2>&1
QUERIES=success; RESULT=success; ERROR_MESSAGE=""; write_report; log "result=success database=${TEMP_DB}"; cleanup; TEMP_CREATED=false
