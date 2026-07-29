#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"
load_database_migration_config

require_value LOCAL_DATABASE_MODE
case "$LOCAL_DATABASE_MODE" in
  direct)
    require_command pg_dump; require_command psql; require_value LOCAL_DATABASE_URL
    local_client="$(pg_dump --version)"
    local_url="$(postgres_cli_url "$LOCAL_DATABASE_URL")"
    local_server="$(psql "$local_url" -tAc 'show server_version')"
    assert_client_can_dump_server "$local_client" "$local_server" "Local pg_dump"
    printf 'Local database mode: direct\nLocal pg_dump: %s\nLocal server: %s\n' "$local_client" "$local_server"
    ;;
  docker)
    require_command docker; require_value LOCAL_POSTGRES_SERVICE; require_value LOCAL_DATABASE_NAME; require_value LOCAL_DATABASE_USER
    local_client="$(local_compose exec -T "$LOCAL_POSTGRES_SERVICE" pg_dump --version)"
    local_server="$(local_compose exec -T "$LOCAL_POSTGRES_SERVICE" psql -U "$LOCAL_DATABASE_USER" -d "$LOCAL_DATABASE_NAME" -tAc 'show server_version')"
    assert_client_can_dump_server "$local_client" "$local_server" "Local pg_dump"
    printf 'Local database mode: docker\nLocal PostgreSQL service: %s\nLocal pg_dump: %s\nLocal server: %s\n' "$LOCAL_POSTGRES_SERVICE" "$local_client" "$local_server"
    ;;
  *) printf 'LOCAL_DATABASE_MODE must be direct or docker.\n' >&2; exit 2 ;;
esac

if [[ -z "${REMOTE_SSH_HOST:-}" || -z "${REMOTE_SSH_USER:-}" ]]; then
  printf 'Remote configuration is incomplete. Set REMOTE_SSH_HOST and REMOTE_SSH_USER before remote checks.\n'
  exit 0
fi

require_remote_database_config
remote_ssh bash -s -- "$REMOTE_APP_DIR" "$(remote_compose_file)" "$REMOTE_POSTGRES_SERVICE" "$REMOTE_DATABASE_NAME" "$REMOTE_DATABASE_USER" <<'REMOTE'
set -Eeuo pipefail
app_dir="$1"; compose_file="$2"; service="$3"; database="$4"; user="$5"
cd "$app_dir"
compose=(docker compose)
[[ -n "$compose_file" ]] && compose+=( -f "$compose_file" )
"${compose[@]}" ps "$service" >/dev/null
client="$("${compose[@]}" exec -T "$service" pg_restore --version)"
server="$("${compose[@]}" exec -T "$service" psql -U "$user" -d "$database" -tAc 'show server_version')"
client_major="$(sed -E 's/[^0-9]*([0-9]+).*/\1/' <<<"$client")"
server_major="$(sed -E 's/[^0-9]*([0-9]+).*/\1/' <<<"$server")"
[[ "$client_major" -ge "$server_major" ]] || { printf 'Remote pg_restore is older than the remote PostgreSQL server.\n' >&2; exit 2; }
printf 'Remote PostgreSQL service: %s\nRemote pg_restore: %s\nRemote server: %s\n' "$service" "$client" "$server"
REMOTE
