#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"
load_database_migration_config
umask 077

artifact_dir="${MIGRATION_ARTIFACT_DIR:-database-migration-artifacts}"
[[ "$artifact_dir" = /* ]] || artifact_dir="$PROJECT_ROOT/$artifact_dir"
mkdir -p "$artifact_dir"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
dump_file="$artifact_dir/rainbow_local_${timestamp}.dump"

require_value LOCAL_DATABASE_MODE
case "$LOCAL_DATABASE_MODE" in
  direct)
    require_command pg_dump; require_command pg_restore; require_command psql; require_value LOCAL_DATABASE_URL
    local_url="$(postgres_cli_url "$LOCAL_DATABASE_URL")"
    client="$(pg_dump --version)"; server="$(psql "$local_url" -tAc 'show server_version')"
    assert_client_can_dump_server "$client" "$server" "Local pg_dump"
    pg_dump --dbname="$local_url" --format=custom --no-owner --no-acl --file="$dump_file"
    ;;
  docker)
    require_command docker; require_value LOCAL_POSTGRES_SERVICE; require_value LOCAL_DATABASE_NAME; require_value LOCAL_DATABASE_USER
    client="$(local_compose exec -T "$LOCAL_POSTGRES_SERVICE" pg_dump --version)"; server="$(local_compose exec -T "$LOCAL_POSTGRES_SERVICE" psql -U "$LOCAL_DATABASE_USER" -d "$LOCAL_DATABASE_NAME" -tAc 'show server_version')"
    assert_client_can_dump_server "$client" "$server" "Local pg_dump"
    local_compose exec -T "$LOCAL_POSTGRES_SERVICE" pg_dump -Fc --no-owner --no-acl -U "$LOCAL_DATABASE_USER" -d "$LOCAL_DATABASE_NAME" > "$dump_file"
    ;;
  *) printf 'LOCAL_DATABASE_MODE must be direct or docker.\n' >&2; exit 2 ;;
esac

[[ -s "$dump_file" ]] || { printf 'Dump is empty; refusing to continue.\n' >&2; rm -f "$dump_file"; exit 1; }
if [[ "$LOCAL_DATABASE_MODE" == "docker" ]]; then
  local_compose exec -T "$LOCAL_POSTGRES_SERVICE" pg_restore -l < "$dump_file" >/dev/null
else
  pg_restore -l "$dump_file" >/dev/null
fi
checksum="$(file_checksum "$dump_file")"
printf '%s  %s\n' "$checksum" "$(basename "$dump_file")" > "$dump_file.sha256"
cat > "$dump_file.manifest" <<EOF
created_at_utc=$timestamp
format=custom
pg_dump_version=$client
source_server_version=$server
sha256=$checksum
EOF
printf 'Local database export complete.\nDump: %s\nChecksum: %s\n' "$dump_file" "$checksum"
