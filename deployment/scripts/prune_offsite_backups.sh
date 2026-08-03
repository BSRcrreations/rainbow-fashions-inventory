#!/usr/bin/env bash
# Restic pruning remains non-destructive until an operator passes --execute.
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib_backup.sh"
OFFSITE_ENV="${RAINBOW_OFFSITE_ENV:-${RAINBOW_SHARED_DIR}/backup-offsite.env}"
[[ -r "$OFFSITE_ENV" ]] || backup_die "Missing protected offsite configuration: $OFFSITE_ENV"
source "$OFFSITE_ENV"
: "${RESTIC_REPOSITORY:?RESTIC_REPOSITORY is required}"
: "${RESTIC_PASSWORD:?RESTIC_PASSWORD is required}"

mode=dry-run
[[ "${1:-}" == "--execute" ]] && mode=execute
[[ -z "${1:-}" || "${1:-}" == "--execute" ]] || backup_die "Usage: $0 [--execute]"
backup_require_command restic
backup_init_log backup-retention.log
backup_lock retention

arguments=(forget --tag rainbow-fashions --keep-daily 30 --keep-weekly 12 --keep-monthly 12)
if [[ "$mode" == dry-run ]]; then
  arguments+=(--dry-run)
else
  [[ "${OFFSITE_RETENTION_APPROVED:-}" == "YES" ]] || backup_die "Set OFFSITE_RETENTION_APPROVED=YES only after reviewing dry-run output."
  arguments+=(--prune)
fi
output="$(restic "${arguments[@]}")"
backup_write_json "${RAINBOW_BACKUP_STATUS_DIR}/latest-retention-report.json" \
  "timestamp=$(backup_now)" "result=SUCCESS" "mode=${mode}" \
  "offsite_policy=daily=30,weekly=12,monthly=12" "repository=$(backup_redact_repository "$RESTIC_REPOSITORY")" \
  "summary=${output}"
backup_log "offsite_retention_completed mode=${mode} repository=$(backup_redact_repository "$RESTIC_REPOSITORY")"
