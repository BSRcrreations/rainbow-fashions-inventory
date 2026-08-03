#!/usr/bin/env bash
# The daily scheduler entry point: no cleanup runs unless both backups succeed.
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${BACKUP_CONFIG_FILE:-/etc/rainbow-fashions/backup.env}"
[[ -r "$CONFIG_FILE" ]] && source "$CONFIG_FILE"
: "${BACKUP_LOCAL_PATH:=/u02/backups}"
mkdir -p "$BACKUP_LOCAL_PATH"
command -v flock >/dev/null || { echo "flock is required" >&2; exit 127; }
exec 9>"$BACKUP_LOCAL_PATH/.backup.lock"
flock -n 9 || { echo "A backup job is already running" >&2; exit 1; }
"$SCRIPT_DIR/backup_postgres.sh"
"$SCRIPT_DIR/backup_uploads.sh"
"$SCRIPT_DIR/cleanup_backups.sh"
