#!/usr/bin/env bash
set -Eeuo pipefail

# Exports DDL only. No customer, product, transaction, or credential data is
# included, so the resulting file can be reviewed and committed when desired.
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"
load_database_migration_config

output_file="${DATABASE_SCHEMA_EXPORT_FILE:-$PROJECT_ROOT/database/local-schema.sql}"
[[ "$output_file" = /* ]] || output_file="$PROJECT_ROOT/$output_file"
mkdir -p "$(dirname "$output_file")"

require_value LOCAL_DATABASE_MODE
case "$LOCAL_DATABASE_MODE" in
  direct)
    require_command pg_dump
    require_command psql
    require_value LOCAL_DATABASE_URL
    local_url="$(postgres_cli_url "$LOCAL_DATABASE_URL")"
    client="$(pg_dump --version)"
    server="$(psql "$local_url" -tAc 'show server_version')"
    assert_client_can_dump_server "$client" "$server" "Local pg_dump"
    pg_dump --dbname="$local_url" --schema-only --no-owner --no-acl --file="$output_file"
    ;;
  docker)
    require_command docker
    require_value LOCAL_POSTGRES_SERVICE
    require_value LOCAL_DATABASE_NAME
    require_value LOCAL_DATABASE_USER
    client="$(local_compose exec -T "$LOCAL_POSTGRES_SERVICE" pg_dump --version)"
    server="$(local_compose exec -T "$LOCAL_POSTGRES_SERVICE" psql -U "$LOCAL_DATABASE_USER" -d "$LOCAL_DATABASE_NAME" -tAc 'show server_version')"
    assert_client_can_dump_server "$client" "$server" "Local pg_dump"
    local_compose exec -T "$LOCAL_POSTGRES_SERVICE" \
      pg_dump --schema-only --no-owner --no-acl -U "$LOCAL_DATABASE_USER" -d "$LOCAL_DATABASE_NAME" \
      > "$output_file"
    ;;
  *)
    printf 'LOCAL_DATABASE_MODE must be direct or docker.\n' >&2
    exit 2
    ;;
esac

[[ -s "$output_file" ]] || {
  printf 'Schema export is empty; refusing to continue.\n' >&2
  exit 1
}

printf 'Local database schema exported to: %s\n' "$output_file"
