#!/usr/bin/env bash
# Apply the checked production environment without recreating the database.
set -Eeuo pipefail

APP_ROOT="${APP_ROOT:-/opt/rainbow-fashions-prod}"
CURRENT_RELEASE="$APP_ROOT/current"
SHARED_ENV_FILE="$APP_ROOT/shared/backend.env"
BACKUP_DIR="$APP_ROOT/backups/manual-hardening"
HEALTH_URL="http://127.0.0.1:8080/health/ready"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-rainbow_prod}"
COMPOSE_OVERRIDE="${COMPOSE_OVERRIDE:-docker-compose.prod.yml}"
POSTGRES_READY_ATTEMPTS=30
HEALTH_READY_ATTEMPTS=30
RETRY_DELAY_SECONDS=2

log() {
  printf '%s\n' "$*"
}

die() {
  log "ERROR: $*" >&2
  exit 1
}

compose() {
  docker compose -p "$COMPOSE_PROJECT_NAME" -f docker-compose.yml -f "$COMPOSE_OVERRIDE" "$@"
}

print_diagnostics() {
  log "Docker Compose status:"
  compose ps || true

  local service
  for service in backend frontend postgres; do
    log "Last 200 lines for ${service}:"
    compose logs --tail=200 "$service" || true
  done
}

on_error() {
  log "Production hardening failed."
}

require_nonempty() {
  local variable_name="$1"

  [[ -n "${!variable_name:-}" ]] || die "${variable_name} must be set."
}

contains_placeholder() {
  local value="$1"
  local normalized_value="${value,,}"

  [[ "$normalized_value" == *"replace-this"* || "$normalized_value" == *"change-me"* || "$normalized_value" == *"example"* ]]
}

wait_for_postgres() {
  local attempt

  for ((attempt = 1; attempt <= POSTGRES_READY_ATTEMPTS; attempt++)); do
    if compose exec -T postgres sh -ec 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; then
      log "PostgreSQL is ready."
      return 0
    fi

    sleep "$RETRY_DELAY_SECONDS"
  done

  log "PostgreSQL did not become ready in time."
  print_diagnostics
  return 1
}

wait_for_application_health() {
  local attempt

  for ((attempt = 1; attempt <= HEALTH_READY_ATTEMPTS; attempt++)); do
    if curl --fail --silent --show-error "$HEALTH_URL" >/dev/null; then
      log "Application health check passed."
      return 0
    fi

    sleep "$RETRY_DELAY_SECONDS"
  done

  log "Application health check failed: ${HEALTH_URL}"
  print_diagnostics
  return 1
}

create_backup() {
  local backup_timestamp
  local backup_file

  backup_timestamp="$(date +%Y%m%d_%H%M%S)"
  mkdir -p "$BACKUP_DIR"
  chmod 700 "$BACKUP_DIR"
  backup_file="$(mktemp "$BACKUP_DIR/postgres-hardening_${backup_timestamp}_XXXXXX.dump")"
  chmod 600 "$backup_file"

  log "Creating PostgreSQL custom-format backup: ${backup_file}"
  compose exec -T postgres sh -ec 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > "$backup_file"
  [[ -s "$backup_file" ]] || die "Backup command completed without producing a backup file."
  log "PostgreSQL backup completed."
}

synchronize_postgres_role_password() {
  log "Synchronizing the PostgreSQL role password."
  printf 'ALTER ROLE "%s" WITH PASSWORD '\''%s'\'';\n' "$POSTGRES_USER" "$POSTGRES_PASSWORD" \
    | compose exec -T postgres sh -ec 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null
  log "PostgreSQL role password synchronized."
}

trap on_error ERR

[[ -d "$APP_ROOT" ]] || die "Application directory does not exist: ${APP_ROOT}"
[[ "$APP_ROOT" == "/opt/rainbow-fashions-prod" ]] || die "APP_ROOT must be /opt/rainbow-fashions-prod."
[[ "$COMPOSE_PROJECT_NAME" == "rainbow_prod" ]] || die "COMPOSE_PROJECT_NAME must be rainbow_prod."
[[ "$COMPOSE_OVERRIDE" == "docker-compose.prod.yml" ]] || die "COMPOSE_OVERRIDE must be docker-compose.prod.yml."
[[ -d "$CURRENT_RELEASE" ]] || die "Current release does not exist: ${CURRENT_RELEASE}"
[[ -s "$SHARED_ENV_FILE" ]] || die "Shared environment file is missing or empty: ${SHARED_ENV_FILE}"
[[ -d "$CURRENT_RELEASE/backend" ]] || die "Backend directory does not exist in the current release."
command -v docker >/dev/null 2>&1 || die "docker is required."
command -v curl >/dev/null 2>&1 || die "curl is required."

set -a
# shellcheck disable=SC1090
source "$SHARED_ENV_FILE"
set +a
export BACKEND_ENV_FILE="$SHARED_ENV_FILE"
export UPLOADS_HOST_PATH="$APP_ROOT/runtime/uploads"
export OPENING_STOCK_IMPORTS_HOST_PATH="$APP_ROOT/runtime/opening-stock-imports"
export BACKUP_STATUS_HOST_PATH="$APP_ROOT/runtime/backups/status"

[[ "${APP_ENV:-}" == "production" ]] || die "APP_ENV must equal production."
[[ "${DEBUG:-}" == "false" ]] || die "DEBUG must equal false."
require_nonempty POSTGRES_DB
require_nonempty POSTGRES_USER
require_nonempty POSTGRES_PASSWORD
require_nonempty DATABASE_URL
require_nonempty JWT_SECRET_KEY
require_nonempty CORS_ORIGINS
[[ "${#JWT_SECRET_KEY}" -ge 64 ]] || die "JWT_SECRET_KEY must be at least 64 characters."

if contains_placeholder "$POSTGRES_PASSWORD" || contains_placeholder "$JWT_SECRET_KEY" || contains_placeholder "$DATABASE_URL"; then
  die "Production environment contains a placeholder secret."
fi

[[ "$POSTGRES_PASSWORD" != "inventory123" ]] || die "POSTGRES_PASSWORD uses a rejected password."
[[ "$POSTGRES_USER" =~ ^[A-Za-z0-9_]+$ ]] || die "POSTGRES_USER may contain only letters, numbers, and underscores."
[[ "$POSTGRES_PASSWORD" =~ ^[[:xdigit:]]+$ ]] || die "POSTGRES_PASSWORD must be hexadecimal."

expected_database_url="postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}"
[[ "$DATABASE_URL" == "$expected_database_url" ]] || die "DATABASE_URL does not match the PostgreSQL environment values."
unset expected_database_url

cd "$CURRENT_RELEASE"
compose config --quiet

log "Starting PostgreSQL."
compose up -d postgres
wait_for_postgres

create_backup
synchronize_postgres_role_password

log "Building application images."
compose build

log "Running Alembic migrations."
compose run --rm backend alembic upgrade head

log "Starting all application services."
compose up -d --remove-orphans
wait_for_application_health

compose ps
log "Production hardening completed successfully."
