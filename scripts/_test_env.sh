#!/usr/bin/env bash
# Shared safeguards for the isolated inventory UAT environment.
set -Eeuo pipefail

TEST_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$TEST_SCRIPT_DIR/.." && pwd)"
TEST_ENV_FILE="${TEST_ENV_FILE:-$PROJECT_ROOT/backend/.env.test}"
TEST_RUNTIME_DIR="$PROJECT_ROOT/.test-runtime"
TEST_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.test.yml"
TEST_COMPOSE_PROJECT="rainbow-inventory-test"

load_test_environment() {
  if [[ ! -s "$TEST_ENV_FILE" ]]; then
    printf 'Missing testing environment file: %s\nCopy backend/.env.test.example to backend/.env.test and set testing-only values.\n' "$TEST_ENV_FILE" >&2
    exit 2
  fi
  set -a
  # shellcheck disable=SC1090
  source "$TEST_ENV_FILE"
  set +a
}

database_name_from_url() {
  local value="$1" without_query path
  without_query="${value%%\?*}"
  path="${without_query##*/}"
  printf '%s' "$path"
}

database_host_from_url() {
  local value="$1" authority
  authority="${value#*://}"
  authority="${authority#*@}"
  authority="${authority%%/*}"
  authority="${authority%%:*}"
  printf '%s' "$authority"
}

assert_testing_database() {
  local database_name database_host
  if [[ "${APP_ENV:-}" != "testing" ]]; then
    printf 'Refusing operation: APP_ENV must be testing.\n' >&2
    exit 2
  fi
  if [[ -z "${DATABASE_URL:-}" ]]; then
    printf 'Refusing operation: DATABASE_URL is required.\n' >&2
    exit 2
  fi
  database_name="$(database_name_from_url "$DATABASE_URL")"
  database_host="$(database_host_from_url "$DATABASE_URL")"
  if [[ "$database_name" != *_test ]]; then
    printf 'Refusing operation: database name must end in _test (got %s).\n' "$database_name" >&2
    exit 2
  fi
  if [[ "$database_host" =~ (178\.238\.237\.182|contaboserver|rainbow-fashions\.in|production|prod-db) ]]; then
    printf 'Refusing operation: production-like database host is not allowed for UAT (%s).\n' "$database_host" >&2
    exit 2
  fi
  printf 'Environment: %s\nDatabase: %s\nHost: %s\n' "$APP_ENV" "$database_name" "$database_host"
}

require_testing_password() {
  if [[ -z "${UAT_TEST_PASSWORD:-}" || "${UAT_TEST_PASSWORD}" == *CHANGE_ME* ]]; then
    printf 'Set a testing-only UAT_TEST_PASSWORD in backend/.env.test before seeding users.\n' >&2
    exit 2
  fi
}

postgres_cli_url() {
  printf '%s' "${1/postgresql+psycopg:/postgresql:}"
}

test_compose() {
  local docker_env="${TEST_DOCKER_ENV_FILE:-$TEST_RUNTIME_DIR/backend.test.docker.env}"
  local uploads_path="${UPLOADS_HOST_PATH:-$TEST_RUNTIME_DIR/uploads}"
  local imports_path="${OPENING_STOCK_IMPORTS_HOST_PATH:-$TEST_RUNTIME_DIR/opening-stock-imports}"
  local backup_status_path="${BACKUP_STATUS_HOST_PATH:-$TEST_RUNTIME_DIR/backup-status}"
  mkdir -p "$uploads_path" "$imports_path" "$backup_status_path"
  BACKEND_ENV_FILE="$docker_env" \
    UPLOADS_HOST_PATH="$uploads_path" \
    OPENING_STOCK_IMPORTS_HOST_PATH="$imports_path" \
    BACKUP_STATUS_HOST_PATH="$backup_status_path" \
    docker compose --project-name "$TEST_COMPOSE_PROJECT" -f "$PROJECT_ROOT/docker-compose.yml" -f "$TEST_COMPOSE_FILE" "$@"
}

write_docker_test_environment() {
  mkdir -p "$TEST_RUNTIME_DIR"
  local target="$TEST_RUNTIME_DIR/backend.test.docker.env"
  # The direct-UAT URL uses localhost:5433. Docker needs the isolated service hostname.
  sed -E 's#@(127\.0\.0\.1|localhost):5433/#@postgres:5432/#' "$TEST_ENV_FILE" > "$target"
  chmod 600 "$target"
  export TEST_DOCKER_ENV_FILE="$target"
}

confirm_test_reset() {
  local database_name="$1"
  printf '\n*** WARNING: RESETTING TEST DATABASE %s ***\n' "$database_name" >&2
  printf 'This command is blocked outside APP_ENV=testing and *_test databases.\n\n' >&2
  if [[ -t 0 ]]; then
    local typed
    read -r -p "Type RESET ${database_name} to continue: " typed
    [[ "$typed" == "RESET $database_name" ]] || { printf 'Reset confirmation did not match.\n' >&2; exit 2; }
  elif [[ "${TEST_DATABASE_RESET_CONFIRM:-}" != "$database_name" ]]; then
    printf 'Non-interactive reset requires TEST_DATABASE_RESET_CONFIRM=%s.\n' "$database_name" >&2
    exit 2
  fi
}

stop_pid_file() {
  local file="$1" expected="$2"
  [[ -f "$file" ]] || return 0
  local pid command
  pid="$(<"$file")"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    command="$(ps -p "$pid" -o command= 2>/dev/null || true)"
    if [[ "$command" == *"$expected"* ]]; then
      kill "$pid"
      printf 'Stopped test process %s.\n' "$pid"
    else
      printf 'Refusing to stop PID %s because it is not a Rainbow test process.\n' "$pid" >&2
    fi
  fi
  rm -f "$file"
}
