#!/usr/bin/env bash
# Remove expired backup artifacts only after current database and uploads jobs pass.
set -Eeuo pipefail

CONFIG_FILE="${BACKUP_CONFIG_FILE:-/etc/rainbow-fashions/backup.env}"
[[ -r "$CONFIG_FILE" ]] && source "$CONFIG_FILE"
: "${BACKUP_LOCAL_PATH:=/u02/backups}"
: "${BACKUP_RETENTION_DAYS:=30}"
: "${BACKUP_LOG_RETENTION_DAYS:=$BACKUP_RETENTION_DAYS}"
dry_run=false
[[ "${1:-}" == "--dry-run" ]] && dry_run=true
[[ $# -le 1 ]] || { echo "Usage: $0 [--dry-run]" >&2; exit 2; }

STATUS_DIR="$BACKUP_LOCAL_PATH/status"; LOG_DIR="$BACKUP_LOCAL_PATH/logs"; LOG_FILE="$LOG_DIR/backup-cleanup.log"
mkdir -p "$LOG_DIR"; chmod 700 "$LOG_DIR"; touch "$LOG_FILE"; chmod 600 "$LOG_FILE"
log() { printf '%s cleanup %s\n' "$(date --iso-8601=seconds 2>/dev/null || date)" "$*" | tee -a "$LOG_FILE" >&2; }
[[ -s "$STATUS_DIR/latest-database-backup.json" && -s "$STATUS_DIR/latest-uploads-backup.json" ]] || { log "Refusing cleanup: a current backup status is missing."; exit 1; }
grep -q '"status":"success"' "$STATUS_DIR/latest-database-backup.json" && grep -q '"status":"success"' "$STATUS_DIR/latest-uploads-backup.json" || { log "Refusing cleanup: latest database and uploads backups must both succeed."; exit 1; }

cleanup_archive_directory() {
  local directory="$1" pattern="$2" newest artifact base
  [[ -d "$directory" ]] || return 0
  newest="$(find "$directory" -maxdepth 1 -type f -name "$pattern" -print | sort | tail -n 1)"
  [[ -n "$newest" && -s "$newest" ]] || { log "Refusing cleanup: no valid backup found in $directory"; return 1; }
  base="$(basename "$newest")"
  while IFS= read -r -d '' artifact; do
    [[ "$(basename "$artifact")" == "$base" || "$(basename "$artifact")" == "${base}.sha256" ]] && continue
    if [[ "$dry_run" == true ]]; then log "DRY-RUN delete $artifact"; else rm -f -- "$artifact" && log "deleted $artifact"; fi
  done < <(find "$directory" -xdev -maxdepth 1 -type f \( -name "$pattern" -o -name "${pattern}.sha256" \) -mtime "+$BACKUP_RETENTION_DAYS" -print0)
}

cleanup_archive_directory "$BACKUP_LOCAL_PATH/database" 'rainbow_inventory_db_*.dump'
cleanup_archive_directory "$BACKUP_LOCAL_PATH/uploads" 'rainbow_inventory_uploads_*.tar.gz'
while IFS= read -r -d '' log_file; do
  [[ "$dry_run" == true ]] && log "DRY-RUN delete $log_file" || { rm -f -- "$log_file"; log "deleted $log_file"; }
done < <(find "$LOG_DIR" -xdev -maxdepth 1 -type f -name '*.log' -mtime "+$BACKUP_LOG_RETENTION_DAYS" -print0)
log "result=success dry_run=${dry_run}"
