#!/usr/bin/env bash
# Deliberately guarded manual restore. It cannot target production unless an
# operator provides the exact target database name as an interactive confirmation.
set -Eeuo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /u02/backups/database/rainbow_inventory_db_YYYY-MM-DD_HH-MM-SS.dump" >&2
  exit 2
fi

CONFIG_FILE="${BACKUP_CONFIG_FILE:-/etc/rainbow-fashions/backup.env}"
[[ -r "$CONFIG_FILE" ]] && source "$CONFIG_FILE"
: "${RESTORE_DB_HOST:?RESTORE_DB_HOST is required}"
: "${RESTORE_DB_PORT:=5432}"
: "${RESTORE_DB_NAME:?RESTORE_DB_NAME is required}"
: "${RESTORE_DB_USER:?RESTORE_DB_USER is required}"
BACKUP_FILE="$1"
[[ -s "$BACKUP_FILE" ]] || { echo "Backup file is missing or empty: $BACKUP_FILE" >&2; exit 2; }
[[ -s "${BACKUP_FILE}.sha256" ]] || { echo "Checksum sidecar is required: ${BACKUP_FILE}.sha256" >&2; exit 2; }

if command -v sha256sum >/dev/null; then
  (cd "$(dirname "$BACKUP_FILE")" && sha256sum --check "$(basename "${BACKUP_FILE}.sha256")")
else
  (cd "$(dirname "$BACKUP_FILE")" && shasum -a 256 --check "$(basename "${BACKUP_FILE}.sha256")")
fi
pg_restore --list "$BACKUP_FILE" >/dev/null

if [[ -t 0 ]]; then
  read -r -p "This replaces all data in ${RESTORE_DB_NAME} on ${RESTORE_DB_HOST}. Type RESTORE ${RESTORE_DB_NAME}: " confirmation
  [[ "$confirmation" == "RESTORE ${RESTORE_DB_NAME}" ]] || { echo "Confirmation did not match." >&2; exit 2; }
elif [[ "${RESTORE_CONFIRM_DATABASE:-}" != "$RESTORE_DB_NAME" ]]; then
  echo "Non-interactive restore requires RESTORE_CONFIRM_DATABASE=${RESTORE_DB_NAME}." >&2
  exit 2
fi

pg_restore --host="$RESTORE_DB_HOST" --port="$RESTORE_DB_PORT" --username="$RESTORE_DB_USER" --dbname="$RESTORE_DB_NAME" --clean --if-exists --no-owner --exit-on-error "$BACKUP_FILE"
echo "Restore completed: ${BACKUP_FILE} -> ${RESTORE_DB_NAME}" >&2
