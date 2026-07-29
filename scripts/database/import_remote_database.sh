#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"
load_database_migration_config

[[ "${1:-}" == "--confirm-replace" && $# -eq 1 ]] || {
  printf 'Usage: %s --confirm-replace\n' "$(basename "$0")" >&2
  printf 'This replaces the remote database only after a verified backup and a second confirmation.\n' >&2
  exit 2
}
require_remote_database_config
require_value REMOTE_BACKEND_SERVICE
require_value REMOTE_BACKUP_DIR
require_value REMOTE_STAGED_DUMP_PATH
[[ "${ALLOW_BACKEND_DOWNTIME:-false}" == "true" ]] || {
  printf 'Set ALLOW_BACKEND_DOWNTIME=true only after an approved maintenance window.\n' >&2
  exit 2
}

backup_result="$("$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/backup_remote_database.sh")"
printf '%s\n' "$backup_result"
backup_path="$(sed -n 's/^REMOTE_BACKUP_PATH=//p' <<<"$backup_result")"
backup_checksum="$(sed -n 's/^REMOTE_BACKUP_CHECKSUM=//p' <<<"$backup_result")"
[[ -n "$backup_path" && "$backup_checksum" =~ ^[A-Fa-f0-9]{64}$ ]] || {
  printf 'Verified remote backup details were not returned; refusing to import.\n' >&2
  exit 1
}

confirm_destructive_action "REPLACE_PRODUCTION_DATABASE" "MIGRATION_IMPORT_CONFIRMATION"

remote_ssh bash -s -- "$REMOTE_APP_DIR" "$(remote_compose_file)" "$REMOTE_POSTGRES_SERVICE" "$REMOTE_DATABASE_NAME" "$REMOTE_DATABASE_USER" "$REMOTE_BACKEND_SERVICE" "$REMOTE_STAGED_DUMP_PATH" "$backup_path" "$backup_checksum" <<'REMOTE'
set -Eeuo pipefail
app_dir="$1"; compose_file="$2"; pg_service="$3"; database="$4"; user="$5"; backend_service="$6"; staged_dump="$7"; backup_path="$8"; backup_checksum="$9"
cd "$app_dir"
compose=(docker compose)
[[ -n "$compose_file" ]] && compose+=( -f "$compose_file" )
checksum() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'; else shasum -a 256 "$1" | awk '{print $1}'; fi
}
test -s "$backup_path"
[[ "$(checksum "$backup_path")" == "$backup_checksum" ]] || { printf 'Production backup checksum no longer matches.\n' >&2; exit 1; }
test -s "$staged_dump"
test -s "$staged_dump.manifest"
source_server_version="$(sed -n 's/^source_server_version=//p' "$staged_dump.manifest")"
[[ -n "$source_server_version" ]] || { printf 'Staged dump manifest is missing source_server_version.\n' >&2; exit 1; }
"${compose[@]}" config --services | grep -Fx "$pg_service" >/dev/null
"${compose[@]}" config --services | grep -Fx "$backend_service" >/dev/null
restore_version="$("${compose[@]}" exec -T "$pg_service" pg_restore --version)"
target_server_version="$("${compose[@]}" exec -T "$pg_service" psql -U "$user" -d "$database" -tAc 'show server_version')"
restore_major="$(sed -E 's/[^0-9]*([0-9]+).*/\1/' <<<"$restore_version")"
source_major="$(sed -E 's/[^0-9]*([0-9]+).*/\1/' <<<"$source_server_version")"
target_major="$(sed -E 's/[^0-9]*([0-9]+).*/\1/' <<<"$target_server_version")"
[[ "$restore_major" -ge "$source_major" && "$restore_major" -ge "$target_major" ]] || { printf 'Remote pg_restore is too old for the source or target PostgreSQL server.\n' >&2; exit 2; }
"${compose[@]}" exec -T "$pg_service" pg_restore -l < "$staged_dump" >/dev/null
restore_backend=0
restart_backend() {
  if [[ "$restore_backend" == "1" ]]; then
    "${compose[@]}" up -d "$backend_service"
  fi
}
trap restart_backend EXIT
"${compose[@]}" stop "$backend_service"
restore_backend=1
"${compose[@]}" exec -T "$pg_service" pg_restore --exit-on-error --clean --if-exists --no-owner --no-acl -U "$user" -d "$database" < "$staged_dump"
"${compose[@]}" run --rm "$backend_service" alembic upgrade heads
restart_backend
restore_backend=0
trap - EXIT
REMOTE

"$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/verify_database_import.sh"
printf 'Import completed. Rollback source: %s\n' "$backup_path"
