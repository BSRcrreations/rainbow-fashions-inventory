#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"
load_database_migration_config

[[ "${1:-}" == "--confirm-rollback" && $# -eq 2 ]] || {
  printf 'Usage: %s --confirm-rollback <remote-backup-path>\n' "$(basename "$0")" >&2
  exit 2
}
rollback_path="$2"
require_remote_database_config
require_value REMOTE_BACKEND_SERVICE
require_value REMOTE_BACKUP_DIR
[[ "${ALLOW_BACKEND_DOWNTIME:-false}" == "true" ]] || {
  printf 'Set ALLOW_BACKEND_DOWNTIME=true only after an approved maintenance window.\n' >&2
  exit 2
}

current_backup_result="$("$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/backup_remote_database.sh")"
printf '%s\n' "$current_backup_result"
confirm_destructive_action "ROLLBACK_PRODUCTION_DATABASE" "MIGRATION_ROLLBACK_CONFIRMATION"

remote_ssh bash -s -- "$REMOTE_APP_DIR" "$(remote_compose_file)" "$REMOTE_POSTGRES_SERVICE" "$REMOTE_DATABASE_NAME" "$REMOTE_DATABASE_USER" "$REMOTE_BACKEND_SERVICE" "$rollback_path" <<'REMOTE'
set -Eeuo pipefail
app_dir="$1"; compose_file="$2"; pg_service="$3"; database="$4"; user="$5"; backend_service="$6"; rollback_path="$7"
cd "$app_dir"
compose=(docker compose)
[[ -n "$compose_file" ]] && compose+=( -f "$compose_file" )
test -s "$rollback_path"
test -s "$rollback_path.manifest"
source_server_version="$(sed -n 's/^source_server_version=//p' "$rollback_path.manifest")"
[[ -n "$source_server_version" ]] || { printf 'Rollback backup manifest is missing source_server_version.\n' >&2; exit 1; }
restore_version="$("${compose[@]}" exec -T "$pg_service" pg_restore --version)"
target_server_version="$("${compose[@]}" exec -T "$pg_service" psql -U "$user" -d "$database" -tAc 'show server_version')"
restore_major="$(sed -E 's/[^0-9]*([0-9]+).*/\1/' <<<"$restore_version")"
source_major="$(sed -E 's/[^0-9]*([0-9]+).*/\1/' <<<"$source_server_version")"
target_major="$(sed -E 's/[^0-9]*([0-9]+).*/\1/' <<<"$target_server_version")"
[[ "$restore_major" -ge "$source_major" && "$restore_major" -ge "$target_major" ]] || { printf 'Remote pg_restore is too old for the rollback backup or target server.\n' >&2; exit 2; }
"${compose[@]}" exec -T "$pg_service" pg_restore -l < "$rollback_path" >/dev/null
restore_backend=0
restart_backend() {
  if [[ "$restore_backend" == "1" ]]; then
    "${compose[@]}" up -d "$backend_service"
  fi
}
trap restart_backend EXIT
"${compose[@]}" stop "$backend_service"
restore_backend=1
"${compose[@]}" exec -T "$pg_service" pg_restore --exit-on-error --clean --if-exists --no-owner --no-acl -U "$user" -d "$database" < "$rollback_path"
restart_backend
restore_backend=0
trap - EXIT
REMOTE

"$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/verify_database_import.sh"
printf 'Rollback completed. The database was restored from: %s\n' "$rollback_path"
