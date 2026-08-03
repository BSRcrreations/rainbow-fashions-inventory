#!/usr/bin/env bash
# Create a verified custom-format production database backup. Retention is a
# separate reviewed action; this script never deletes valid backup sets.
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deployment/scripts/lib_backup.sh
source "${SCRIPT_DIR}/lib_backup.sh"

backup_require_command docker
backup_require_command python3
backup_init_log database-backup.log
backup_lock database-backup
backup_load_backend_env
backup_cleanup_partials

timestamp="$(backup_timestamp)"
date_path="$(date -u '+%Y/%m/%d')"
database_dir="${RAINBOW_BACKUP_ROOT}/database/${date_path}"
backup_name="rainbow_inventory_${timestamp}.dump"
backup_file="${database_dir}/${backup_name}"
partial_file="${backup_file}.partial"
checksum_file="${backup_file}.sha256"
metadata_file="${backup_file}.metadata.json"
started_epoch="$(date +%s)"
container="$(backup_postgres_container)"
image="$(backup_postgres_image)"
status_file="${RAINBOW_BACKUP_STATUS_DIR}/latest-database-backup.json"

mkdir -p "$database_dir"
chmod 700 "$database_dir"
umask 077

write_failure() {
  local exit_code="$1"
  rm -f "$partial_file"
  backup_write_json "$status_file" \
    "timestamp=$(backup_now)" "status=FAILED" "dump_filename=${backup_name}" \
    "message=Database backup failed; see ${BACKUP_LOG_FILE}" "exit_code=${exit_code}"
}
trap 'code=$?; write_failure "$code"; exit "$code"' ERR

backup_log "database_backup_started database=${POSTGRES_DB} dump=${backup_name}"
# The password remains in the running database container environment; do not
# pass it as a host-side argument or copy it into the backup metadata.
docker exec -i "$container" sh -ceu '
  export PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required by pg_dump}"
  exec pg_dump -Fc -U "$POSTGRES_USER" -d "$POSTGRES_DB"
' > "$partial_file"
[[ -s "$partial_file" ]] || backup_die "pg_dump produced an empty dump."

# Verify using a client from the running PostgreSQL image, mounted read-only.
docker run --rm --network none -v "${database_dir}:/backup:ro" "$image" \
  pg_restore --list "/backup/${backup_name}.partial" >/dev/null
mv "$partial_file" "$backup_file"
chmod 600 "$backup_file"
checksum="$(backup_sha256 "$backup_file")"
printf '%s  %s\n' "$checksum" "$backup_name" > "$checksum_file"
chmod 600 "$checksum_file"
backup_check_sha256 "$backup_file" || backup_die "Checksum verification failed after backup creation."

finished_at="$(backup_now)"
duration="$(( $(date +%s) - started_epoch ))"
size="$(backup_file_size "$backup_file")"
postgres_version="$(docker exec -i "$container" sh -ceu 'export PGPASSWORD="${POSTGRES_PASSWORD:?}"; psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SHOW server_version"')"
backup_write_json "$metadata_file" \
  "timestamp=${finished_at}" "hostname=$(hostname)" "database=${POSTGRES_DB}" \
  "postgresql_version=${postgres_version}" "dump_filename=${backup_name}" \
  "dump_size_bytes=${size}" "sha256=${checksum}" "deployed_git_commit=$(backup_deployed_commit)" \
  "docker_compose_project=$(backup_compose_project)" "backup_duration_seconds=${duration}" "status=SUCCESS"
backup_write_json "$status_file" \
  "timestamp=${finished_at}" "status=SUCCESS" "dump_path=${backup_file}" \
  "dump_filename=${backup_name}" "dump_size_bytes=${size}" "sha256=${checksum}" \
  "pg_restore_list=SUCCESS" "duration_seconds=${duration}"
backup_log "database_backup_succeeded dump=${backup_name} size_bytes=${size} duration_seconds=${duration}"
