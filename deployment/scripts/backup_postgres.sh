#!/usr/bin/env bash
# Create a verified PostgreSQL custom-format backup. This script is safe to run
# from systemd after /etc/rainbow-fashions/backup.env has been protected (0600).
set -Eeuo pipefail

CONFIG_FILE="${BACKUP_CONFIG_FILE:-/etc/rainbow-fashions/backup.env}"
if [[ -r "$CONFIG_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$CONFIG_FILE"
fi

: "${BACKUP_DB_HOST:?BACKUP_DB_HOST is required}"
: "${BACKUP_DB_PORT:=5432}"
: "${BACKUP_DB_NAME:?BACKUP_DB_NAME is required}"
: "${BACKUP_DB_USER:?BACKUP_DB_USER is required}"
: "${BACKUP_LOCAL_PATH:=/u02/backups}"
: "${BACKUP_RETENTION_DAYS:=30}"

[[ "$BACKUP_DB_PORT" =~ ^[0-9]+$ ]] || { echo "BACKUP_DB_PORT must be numeric" >&2; exit 2; }
[[ "$BACKUP_RETENTION_DAYS" =~ ^[1-9][0-9]*$ ]] || { echo "BACKUP_RETENTION_DAYS must be a positive integer" >&2; exit 2; }
if [[ -n "${PGPASSFILE:-}" ]]; then
  [[ -f "$PGPASSFILE" ]] || { echo "PGPASSFILE does not exist" >&2; exit 2; }
  [[ "$(stat -c '%a' "$PGPASSFILE" 2>/dev/null || stat -f '%Lp' "$PGPASSFILE")" == "600" ]] || { echo "PGPASSFILE must have 0600 permissions" >&2; exit 2; }
fi

DATABASE_DIR="$BACKUP_LOCAL_PATH/database"
STATUS_DIR="$BACKUP_LOCAL_PATH/status"
LOG_DIR="$BACKUP_LOCAL_PATH/logs"
LOG_FILE="$LOG_DIR/database-backup.log"
STATUS_FILE="$STATUS_DIR/latest-database-backup.json"
TIMESTAMP="$(date '+%Y-%m-%d_%H-%M-%S')"
BACKUP_NAME="rainbow_inventory_db_${TIMESTAMP}.dump"
BACKUP_FILE="$DATABASE_DIR/$BACKUP_NAME"
PARTIAL_FILE="${BACKUP_FILE}.partial"
STARTED_AT="$(date --iso-8601=seconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S%z')"
START_EPOCH="$(date +%s)"
RESULT="failed"
FILE_SIZE=0
CHECKSUM=""

mkdir -p "$DATABASE_DIR" "$STATUS_DIR" "$LOG_DIR"
chmod 700 "$DATABASE_DIR" "$STATUS_DIR" "$LOG_DIR"
touch "$LOG_FILE"
chmod 600 "$LOG_FILE"
umask 077

log() { printf '%s database-backup %s\n' "$(date --iso-8601=seconds 2>/dev/null || date)" "$*" | tee -a "$LOG_FILE" >&2; }
json_escape() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }
write_status() {
  local finished_at duration message
  finished_at="$(date --iso-8601=seconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S%z')"
  duration="$(( $(date +%s) - START_EPOCH ))"
  message="${1:-}"
  printf '{"component":"database","status":"%s","started_at":"%s","finished_at":"%s","file":"%s","file_size_bytes":%s,"sha256":"%s","duration_seconds":%s,"message":"%s"}\n' \
    "$RESULT" "$STARTED_AT" "$finished_at" "$BACKUP_NAME" "$FILE_SIZE" "$CHECKSUM" "$duration" "$(json_escape "$message")" > "${STATUS_FILE}.partial"
  chmod 600 "${STATUS_FILE}.partial"
  mv "${STATUS_FILE}.partial" "$STATUS_FILE"
}
on_error() {
  local code="$?"
  rm -f "$PARTIAL_FILE"
  write_status "Backup failed (exit ${code}); see ${LOG_FILE}."
  log "result=failed exit_code=${code} file=${BACKUP_NAME}"
  exit "$code"
}
trap on_error ERR
fail() {
  log "$1"
  write_status "$1"
  exit "${2:-1}"
}

command -v pg_dump >/dev/null || fail "pg_dump is not installed" 127
command -v pg_restore >/dev/null || fail "pg_restore is not installed" 127
if command -v sha256sum >/dev/null; then SHA256=(sha256sum); else SHA256=(shasum -a 256); fi

log "start=${STARTED_AT} database=${BACKUP_DB_NAME} host=${BACKUP_DB_HOST} file=${BACKUP_NAME}"
pg_dump --host="$BACKUP_DB_HOST" --port="$BACKUP_DB_PORT" --username="$BACKUP_DB_USER" --dbname="$BACKUP_DB_NAME" --format=custom --compress=9 --file="$PARTIAL_FILE"
[[ -s "$PARTIAL_FILE" ]] || fail "pg_dump produced an empty backup"
pg_restore --list "$PARTIAL_FILE" >/dev/null
mv "$PARTIAL_FILE" "$BACKUP_FILE"
chmod 600 "$BACKUP_FILE"
FILE_SIZE="$(stat -c '%s' "$BACKUP_FILE" 2>/dev/null || stat -f '%z' "$BACKUP_FILE")"
CHECKSUM="$(${SHA256[@]} "$BACKUP_FILE" | awk '{print $1}')"
printf '%s  %s\n' "$CHECKSUM" "$BACKUP_NAME" > "${BACKUP_FILE}.sha256"
chmod 600 "${BACKUP_FILE}.sha256"

# Keep dumps and their checksum files for the configured retention period.
find "$DATABASE_DIR" -xdev -type f \( -name 'rainbow_inventory_db_*.dump' -o -name 'rainbow_inventory_db_*.dump.sha256' \) -mtime "+$BACKUP_RETENTION_DAYS" -delete
RESULT="success"
write_status "Backup verified and retained for ${BACKUP_RETENTION_DAYS} days."
log "finish=$(date --iso-8601=seconds 2>/dev/null || date) result=success file=${BACKUP_NAME} size_bytes=${FILE_SIZE} sha256=${CHECKSUM}"
