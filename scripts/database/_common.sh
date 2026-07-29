#!/usr/bin/env bash
set -Eeuo pipefail

DATABASE_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$DATABASE_SCRIPT_DIR/../.." && pwd)"
DATABASE_MIGRATION_ENV_FILE="${DATABASE_MIGRATION_ENV_FILE:-$DATABASE_SCRIPT_DIR/database-migration.env}"

load_database_migration_config() {
  if [[ -f "$DATABASE_MIGRATION_ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$DATABASE_MIGRATION_ENV_FILE"
    set +a
  fi
}

require_value() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    printf 'Missing required configuration: %s\n' "$name" >&2
    exit 2
  fi
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || { printf 'Required command not found: %s\n' "$1" >&2; exit 2; }
}

file_checksum() {
  local file="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$file" | awk '{print $1}'
  else
    shasum -a 256 "$file" | awk '{print $1}'
  fi
}

postgres_cli_url() {
  local url="$1"
  sed 's#^postgresql+psycopg://#postgresql://#' <<<"$url"
}

version_major() {
  sed -E 's/[^0-9]*([0-9]+).*/\1/' <<<"$1"
}

assert_client_can_dump_server() {
  local client="$1" server="$2" label="$3"
  local client_major server_major
  client_major="$(version_major "$client")"
  server_major="$(version_major "$server")"
  if [[ -z "$client_major" || -z "$server_major" || "$client_major" -lt "$server_major" ]]; then
    printf '%s client major version (%s) must be at least the server major version (%s).\n' "$label" "$client" "$server" >&2
    exit 2
  fi
}

local_compose() {
  if [[ -n "${LOCAL_COMPOSE_FILE:-}" ]]; then
    docker compose -f "$LOCAL_COMPOSE_FILE" "$@"
  else
    (cd "$PROJECT_ROOT" && docker compose "$@")
  fi
}

require_remote_connection() {
  require_value REMOTE_SSH_HOST
  require_value REMOTE_SSH_USER
  : "${REMOTE_SSH_PORT:=22}"
}

remote_ssh() {
  ssh -p "$REMOTE_SSH_PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$REMOTE_SSH_USER@$REMOTE_SSH_HOST" "$@"
}

remote_scp() {
  scp -P "$REMOTE_SSH_PORT" -o BatchMode=yes -o StrictHostKeyChecking=accept-new "$@"
}

require_remote_database_config() {
  require_remote_connection
  require_value REMOTE_APP_DIR
  require_value REMOTE_POSTGRES_SERVICE
  require_value REMOTE_DATABASE_NAME
  require_value REMOTE_DATABASE_USER
}

remote_compose_file() {
  printf '%s' "${REMOTE_COMPOSE_FILE:-}"
}

confirm_destructive_action() {
  local expected="$1" variable="$2"
  if [[ -t 0 ]]; then
    local typed
    read -r -p "Type $expected to continue: " typed
    [[ "$typed" == "$expected" ]] || { printf 'Confirmation did not match.\n' >&2; exit 2; }
  elif [[ "${!variable:-}" != "$expected" ]]; then
    printf 'Non-interactive execution requires protected %s=%s.\n' "$variable" "$expected" >&2
    exit 2
  fi
}
