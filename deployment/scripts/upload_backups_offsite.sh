#!/usr/bin/env bash
# Upload verified database and application-upload archives to encrypted remote storage (restic).
set -Eeuo pipefail

CONFIG_FILE="${BACKUP_CONFIG_FILE:-/etc/rainbow-fashions/backup.env}"
[[ -r "$CONFIG_FILE" ]] || { echo "Missing protected backup configuration: $CONFIG_FILE" >&2; exit 2; }
# shellcheck disable=SC1090
source "$CONFIG_FILE"
: "${BACKUP_LOCAL_PATH:=/u02/backups}"
: "${RESTIC_REPOSITORY:?RESTIC_REPOSITORY is required}"
: "${RESTIC_PASSWORD:?RESTIC_PASSWORD is required}"
: "${BACKUP_RETENTION_DAYS:=30}"

STATUS_DIR="$BACKUP_LOCAL_PATH/status"; LOG_DIR="$BACKUP_LOCAL_PATH/logs"; STATUS_FILE="$STATUS_DIR/latest-offsite-backup.json"
mkdir -p "$STATUS_DIR" "$LOG_DIR"; chmod 700 "$STATUS_DIR" "$LOG_DIR"; umask 077
START="$(date --iso-8601=seconds 2>/dev/null || date)"; START_EPOCH="$(date +%s)"; RESULT=failed; SNAPSHOT=""
log() { printf '%s offsite-backup %s\n' "$(date --iso-8601=seconds 2>/dev/null || date)" "$*" | tee -a "$LOG_DIR/offsite-backup.log" >&2; }
write_status() { local msg="$1"; printf '{"component":"offsite","status":"%s","started_at":"%s","finished_at":"%s","snapshot_id":"%s","duration_seconds":%s,"message":"%s"}\n' "$RESULT" "$START" "$(date --iso-8601=seconds 2>/dev/null || date)" "$SNAPSHOT" "$(( $(date +%s) - START_EPOCH ))" "${msg//\"/\\\"}" > "$STATUS_FILE"; chmod 600 "$STATUS_FILE"; }
trap 'code=$?; write_status "Offsite upload failed (exit ${code})."; exit "$code"' ERR

command -v restic >/dev/null || { log "restic is not installed"; exit 127; }
database_count=0
uploads_count=0
for directory in "$BACKUP_LOCAL_PATH/database" "$BACKUP_LOCAL_PATH/uploads"; do
  [[ -d "$directory" ]] || { log "Backup directory is missing: $directory"; exit 1; }
  while IFS= read -r -d '' archive; do
    if [[ "$directory" == "$BACKUP_LOCAL_PATH/database" ]]; then database_count=$((database_count + 1)); else uploads_count=$((uploads_count + 1)); fi
    [[ -s "$archive" && -s "${archive}.sha256" ]] || { log "Archive or checksum missing: $archive"; exit 1; }
    if command -v sha256sum >/dev/null; then (cd "$(dirname "$archive")" && sha256sum --check "$(basename "${archive}.sha256")") >/dev/null; else (cd "$(dirname "$archive")" && shasum -a 256 --check "$(basename "${archive}.sha256")") >/dev/null; fi
  done < <(find "$directory" -maxdepth 1 -type f \( -name '*.dump' -o -name '*.tar.gz' \) -print0)
done
[[ "$database_count" -gt 0 ]] || { log "No database backups are available for offsite upload"; exit 1; }
[[ "$uploads_count" -gt 0 ]] || { log "No uploads backups are available for offsite upload"; exit 1; }

restic cat config >/dev/null
backup_json="$(restic backup --json --tag rainbow-fashions --tag database --tag uploads "$BACKUP_LOCAL_PATH/database" "$BACKUP_LOCAL_PATH/uploads")"
SNAPSHOT="$(printf '%s\n' "$backup_json" | sed -n 's/.*"snapshot_id":"\([^"]*\)".*/\1/p' | tail -n 1)"
[[ -n "$SNAPSHOT" ]] || { log "restic did not report a snapshot"; exit 1; }
# Retain at least 30 daily points remotely as well as local copies.
restic forget --prune --keep-daily="$BACKUP_RETENTION_DAYS" --keep-weekly=8 --tag rainbow-fashions
RESULT=success; write_status "Encrypted database and uploads backup uploaded."; log "result=success snapshot=${SNAPSHOT}"
