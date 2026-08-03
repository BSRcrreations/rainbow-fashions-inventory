#!/usr/bin/env bash
# Upload verified local recovery material to an encrypted Restic repository.
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deployment/scripts/lib_backup.sh
source "${SCRIPT_DIR}/lib_backup.sh"

OFFSITE_ENV="${RAINBOW_OFFSITE_ENV:-${RAINBOW_SHARED_DIR}/backup-offsite.env}"
[[ -r "$OFFSITE_ENV" ]] || backup_die "Missing protected offsite configuration: $OFFSITE_ENV"
# shellcheck disable=SC1090
source "$OFFSITE_ENV"
: "${RESTIC_REPOSITORY:?RESTIC_REPOSITORY is required}"
: "${RESTIC_PASSWORD:?RESTIC_PASSWORD is required}"

backup_require_command restic
backup_require_command python3
backup_init_log offsite-backup.log
backup_lock offsite-backup
backup_cleanup_partials

status_file="${RAINBOW_BACKUP_STATUS_DIR}/latest-offsite-backup.json"
started_epoch="$(date +%s)"
files_list="$(mktemp "${TMPDIR:-/tmp}/rainbow-offsite-files.XXXXXX")"
trap 'rm -f "$files_list"' EXIT

find "$RAINBOW_BACKUP_ROOT/database" -type f -name 'rainbow_inventory_*.dump' -print0 2>/dev/null |
  while IFS= read -r -d '' dump; do
    [[ "$dump" != *.partial ]] || backup_die "Partial database backup cannot be uploaded: $dump"
    backup_check_sha256 "$dump" || backup_die "Database backup checksum is missing or invalid: $dump"
    metadata="${dump}.metadata.json"
    [[ -s "$metadata" ]] || backup_die "Database backup metadata is missing: $dump"
    printf '%s\0%s\0%s\0' "$dump" "${dump}.sha256" "$metadata"
  done > "$files_list"

[[ -s "$files_list" ]] || backup_die "No verified local PostgreSQL dump is available for offsite upload."
find "$RAINBOW_BACKUP_ROOT/uploads" -type f -name 'rainbow_uploads_*.tar.gz' -print0 2>/dev/null |
  while IFS= read -r -d '' archive; do
    backup_check_sha256 "$archive" || backup_die "Uploads archive checksum is missing or invalid: $archive"
    manifest="${archive}.manifest.json"
    [[ -s "$manifest" ]] || backup_die "Uploads manifest is missing: $archive"
    printf '%s\0%s\0%s\0' "$archive" "${archive}.sha256" "$manifest"
  done >> "$files_list"
[[ -d "${RAINBOW_BACKUP_ROOT}/restore-tests" ]] && find "${RAINBOW_BACKUP_ROOT}/restore-tests" -type f -name '*.json' -print0 >> "$files_list"
[[ -d "$RAINBOW_BACKUP_STATUS_DIR" ]] && find "$RAINBOW_BACKUP_STATUS_DIR" -type f -name '*.json' -print0 >> "$files_list"

# Restic applies authenticated encryption client-side. It will refuse a missing
# repository instead of silently creating a destination with a typo.
restic cat config >/dev/null
backup_log "offsite_backup_started repository=$(backup_redact_repository "$RESTIC_REPOSITORY")"
backup_json="$(restic backup --json --tag rainbow-fashions --tag production --tag database --tag uploads \
  --files-from-raw "$files_list")"
snapshot_id="$(printf '%s\n' "$backup_json" | sed -n 's/.*"snapshot_id":"\([^"]*\)".*/\1/p' | tail -n 1)"
[[ -n "$snapshot_id" ]] || backup_die "Restic did not return a snapshot identifier."
restic snapshots --json | python3 - "$snapshot_id" <<'PY'
import json
import sys
snapshot_id = sys.argv[1]
snapshots = json.load(sys.stdin)
if not any(snapshot.get('short_id') == snapshot_id or snapshot.get('id', '').startswith(snapshot_id) for snapshot in snapshots):
    raise SystemExit('Created Restic snapshot was not found.')
PY

file_count="$(tr -cd '\0' < "$files_list" | wc -c | tr -d ' ')"
total_bytes="$(python3 - "$files_list" <<'PY'
import os
import sys
total = 0
for raw in open(sys.argv[1], 'rb').read().split(b'\0'):
    if raw:
        total += os.path.getsize(raw.decode('utf-8', 'surrogateescape'))
print(total)
PY
)"
duration="$(( $(date +%s) - started_epoch ))"
backup_write_json "$status_file" \
  "timestamp=$(backup_now)" "status=SUCCESS" "snapshot_id=${snapshot_id}" \
  "hostname=$(hostname)" "files_included=${file_count}" "total_bytes=${total_bytes}" \
  "duration_seconds=${duration}" "repository=$(backup_redact_repository "$RESTIC_REPOSITORY")" \
  "encryption=RESTIC_CLIENT_SIDE_ENCRYPTION"
backup_log "offsite_backup_succeeded snapshot=${snapshot_id} files=${file_count} duration_seconds=${duration}"
