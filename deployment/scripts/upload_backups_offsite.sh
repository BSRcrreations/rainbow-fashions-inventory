#!/usr/bin/env bash
# Upload verified local database backups to an encrypted restic repository.
set -Eeuo pipefail

APP_ROOT="/opt/rainbow-fashions"
CURRENT_RELEASE="$APP_ROOT/current"
CONFIG_FILE="$APP_ROOT/shared/backup-offsite.env"
BACKUP_ROOT="$APP_ROOT/backups/database"
STATUS_DIR="$APP_ROOT/backups/status"
STATUS_FILE="$STATUS_DIR/latest-offsite-backup.json"
CHECK_MARKER="$STATUS_DIR/last-restic-check-at"
LOG_DIR="/var/log/rainbow-fashions"
LOG_FILE="$LOG_DIR/offsite-backup.log"
LOCK_FILE="/run/lock/rainbow-offsite-backup.lock"

log() {
  printf '%s %s\n' "$(date --iso-8601=seconds)" "$*"
}

die() {
  log "ERROR: $*"
  exit 1
}

require_value() {
  local variable_name="$1"
  [[ -n "${!variable_name:-}" ]] || die "${variable_name} must be set in the offsite backup configuration."
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

checksum_file() {
  local backup_file="$1"
  local checksum_path="${backup_file}.sha256"
  local backup_dir

  [[ -s "$checksum_path" ]] || die "Checksum file is missing or empty for $(basename "$backup_file")."
  backup_dir="$(dirname "$backup_file")"

  if command_exists sha256sum; then
    (cd "$backup_dir" && sha256sum --check "$(basename "$checksum_path")") >/dev/null
  elif command_exists shasum; then
    (cd "$backup_dir" && shasum -a 256 --check "$(basename "$checksum_path")") >/dev/null
  else
    die "sha256sum or shasum is required to verify local backup checksums."
  fi
}

metadata_file_for() {
  local backup_file="$1"

  if [[ -s "${backup_file}.metadata" ]]; then
    printf '%s\n' "${backup_file}.metadata"
  elif [[ -s "${backup_file}.metadata.json" ]]; then
    printf '%s\n' "${backup_file}.metadata.json"
  else
    return 1
  fi
}

verify_local_backups() {
  local backup_file
  local metadata_file
  local backup_count=0

  if find "$BACKUP_ROOT" -type f -name '*.partial' -print -quit | grep -q .; then
    die "Refusing offsite upload while incomplete .partial database backups exist."
  fi

  while IFS= read -r -d '' backup_file; do
    backup_count=$((backup_count + 1))
    [[ -s "$backup_file" ]] || die "Backup dump is empty: $(basename "$backup_file")."
    metadata_file="$(metadata_file_for "$backup_file")" || die "Metadata file is missing for $(basename "$backup_file")."
    checksum_file "$backup_file"
    docker compose exec -T postgres pg_restore --list < "$backup_file" >/dev/null
    log "Verified local backup $(basename "$backup_file") and $(basename "$metadata_file")."
  done < <(find "$BACKUP_ROOT" -type f -name 'rainbow_inventory_*.dump' -print0)

  [[ "$backup_count" -gt 0 ]] || die "No database backup dumps were found in ${BACKUP_ROOT}."
}

run_repository_check_if_due() {
  local check_interval_days
  local now_epoch
  local last_check_epoch=0

  check_interval_days="${RESTIC_CHECK_INTERVAL_DAYS:-7}"
  [[ "$check_interval_days" =~ ^[1-9][0-9]*$ ]] || die "RESTIC_CHECK_INTERVAL_DAYS must be a positive integer."
  now_epoch="$(date +%s)"

  if [[ -s "$CHECK_MARKER" ]]; then
    last_check_epoch="$(cat "$CHECK_MARKER")"
    [[ "$last_check_epoch" =~ ^[0-9]+$ ]] || last_check_epoch=0
  fi

  if (( now_epoch - last_check_epoch >= check_interval_days * 86400 )); then
    log "Running scheduled restic repository integrity check."
    restic check
    printf '%s\n' "$now_epoch" > "$CHECK_MARKER"
  fi
}

write_status_file() {
  local timestamp="$1"
  local snapshot_id="$2"
  local files_uploaded="$3"
  local duration_seconds="$4"
  local hostname

  hostname="$(hostname -f 2>/dev/null || hostname)"
  umask 077
  cat > "${STATUS_FILE}.partial" <<EOF
{
  "timestamp": "${timestamp}",
  "snapshot_id": "${snapshot_id}",
  "files_uploaded": ${files_uploaded},
  "status": "success",
  "duration_seconds": ${duration_seconds},
  "hostname": "${hostname}"
}
EOF
  mv "${STATUS_FILE}.partial" "$STATUS_FILE"
}

[[ -d "$CURRENT_RELEASE" ]] || die "Current release directory is missing: ${CURRENT_RELEASE}"
[[ -s "$CONFIG_FILE" ]] || die "Offsite backup configuration is missing or empty: ${CONFIG_FILE}"
command_exists restic || die "restic is required before offsite backups can run."
command_exists flock || die "flock is required before offsite backups can run."
command_exists docker || die "docker is required to validate database backups."

mkdir -p "$LOG_DIR" "$STATUS_DIR"
chmod 750 "$LOG_DIR" "$STATUS_DIR"
touch "$LOG_FILE"
chmod 640 "$LOG_FILE"
exec >> "$LOG_FILE" 2>&1

exec 9>"$LOCK_FILE"
flock -n 9 || die "Another offsite backup upload is already running."

set -a
# shellcheck disable=SC1090
source "$CONFIG_FILE"
set +a

require_value BACKUP_PROVIDER
require_value RESTIC_REPOSITORY
require_value RESTIC_PASSWORD

case "$BACKUP_PROVIDER" in
  s3)
    [[ "$RESTIC_REPOSITORY" == s3:* ]] || die "RESTIC_REPOSITORY must use the s3: backend for BACKUP_PROVIDER=s3."
    require_value AWS_ACCESS_KEY_ID
    require_value AWS_SECRET_ACCESS_KEY
    require_value AWS_DEFAULT_REGION
    ;;
  sftp)
    [[ "$RESTIC_REPOSITORY" == sftp:* ]] || die "RESTIC_REPOSITORY must use the sftp: backend for BACKUP_PROVIDER=sftp."
    [[ -z "${AWS_ACCESS_KEY_ID:-}" && -z "${AWS_SECRET_ACCESS_KEY:-}" && -z "${AWS_DEFAULT_REGION:-}" ]] || die "S3 credentials must not be present in an SFTP backup configuration."
    ;;
  *)
    die "BACKUP_PROVIDER must be s3 or sftp."
    ;;
esac

cd "$CURRENT_RELEASE"
start_epoch="$(date +%s)"
log "Starting encrypted offsite database backup upload."
verify_local_backups

# This succeeds only for an existing, reachable restic repository. Repository
# initialization is intentionally not automated because the target must be
# explicitly confirmed by an operator first.
restic cat config >/dev/null
run_repository_check_if_due

files_uploaded="$(find "$BACKUP_ROOT" -type f ! -name '*.partial' | wc -l | tr -d ' ')"
backup_json="$(restic backup --json --tag rainbow-fashions --tag database --tag production "$BACKUP_ROOT")"
snapshot_id="$(printf '%s\n' "$backup_json" | sed -n 's/.*"snapshot_id":"\([^"]*\)".*/\1/p' | tail -n 1)"
[[ -n "$snapshot_id" ]] || die "restic completed without reporting a snapshot ID."
restic snapshots --json "$snapshot_id" | grep -q "\"id\":\"${snapshot_id}"

end_epoch="$(date +%s)"
timestamp="$(date --iso-8601=seconds)"
write_status_file "$timestamp" "$snapshot_id" "$files_uploaded" "$((end_epoch - start_epoch))"
log "Offsite backup upload completed successfully with snapshot ${snapshot_id}."
