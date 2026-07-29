#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"
load_database_migration_config
umask 077

require_remote_database_config
require_value REMOTE_BACKUP_DIR

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
remote_ssh bash -s -- "$REMOTE_APP_DIR" "$(remote_compose_file)" "$REMOTE_POSTGRES_SERVICE" "$REMOTE_DATABASE_NAME" "$REMOTE_DATABASE_USER" "$REMOTE_BACKUP_DIR" "$timestamp" <<'REMOTE'
set -Eeuo pipefail
app_dir="$1"; compose_file="$2"; service="$3"; database="$4"; user="$5"; backup_dir="$6"; timestamp="$7"
cd "$app_dir"
compose=(docker compose)
[[ -n "$compose_file" ]] && compose+=( -f "$compose_file" )
mkdir -p -- "$backup_dir"
umask 077
backup_file="$backup_dir/rainbow_production_before_import_${timestamp}.dump"

"${compose[@]}" ps "$service" >/dev/null
client="$("${compose[@]}" exec -T "$service" pg_dump --version)"
server="$("${compose[@]}" exec -T "$service" psql -U "$user" -d "$database" -tAc 'show server_version')"
client_major="$(sed -E 's/[^0-9]*([0-9]+).*/\1/' <<<"$client")"
server_major="$(sed -E 's/[^0-9]*([0-9]+).*/\1/' <<<"$server")"
[[ "$client_major" -ge "$server_major" ]] || { printf 'Remote pg_dump is older than the server.\n' >&2; exit 2; }

"${compose[@]}" exec -T "$service" pg_dump -Fc --no-owner --no-acl -U "$user" -d "$database" > "$backup_file"
[[ -s "$backup_file" ]] || { printf 'Remote backup is empty.\n' >&2; rm -f -- "$backup_file"; exit 1; }
"${compose[@]}" exec -T "$service" pg_restore -l < "$backup_file" >/dev/null
if command -v sha256sum >/dev/null 2>&1; then
  checksum="$(sha256sum "$backup_file" | awk '{print $1}')"
else
  checksum="$(shasum -a 256 "$backup_file" | awk '{print $1}')"
fi
printf '%s  %s\n' "$checksum" "$(basename "$backup_file")" > "$backup_file.sha256"
printf 'created_at_utc=%s\nformat=custom\npg_dump_version=%s\nsource_server_version=%s\nsha256=%s\n' "$timestamp" "$client" "$server" "$checksum" > "$backup_file.manifest"
printf 'REMOTE_BACKUP_PATH=%s\nREMOTE_BACKUP_CHECKSUM=%s\n' "$backup_file" "$checksum"
REMOTE
