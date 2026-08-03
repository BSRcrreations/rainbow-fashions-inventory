#!/usr/bin/env bash
# Shared, host-side helpers for Rainbow Fashions recovery tooling. Scripts in
# this directory deliberately source only protected files outside the release.
set -Eeuo pipefail

RAINBOW_APP_ROOT="${RAINBOW_APP_ROOT:-/opt/rainbow-fashions}"
RAINBOW_CURRENT_DIR="${RAINBOW_CURRENT_DIR:-${RAINBOW_APP_ROOT}/current}"
RAINBOW_SHARED_DIR="${RAINBOW_SHARED_DIR:-${RAINBOW_APP_ROOT}/shared}"
RAINBOW_BACKEND_ENV="${RAINBOW_BACKEND_ENV:-${RAINBOW_SHARED_DIR}/backend.env}"
RAINBOW_BACKUP_ROOT="${RAINBOW_BACKUP_ROOT:-${RAINBOW_APP_ROOT}/backups}"
RAINBOW_BACKUP_STATUS_DIR="${RAINBOW_BACKUP_STATUS_DIR:-${RAINBOW_BACKUP_ROOT}/status}"
RAINBOW_BACKUP_LOG_DIR="${RAINBOW_BACKUP_LOG_DIR:-/var/log/rainbow-fashions}"

backup_die() {
  printf '%s\n' "$*" >&2
  exit 1
}

backup_require_command() {
  command -v "$1" >/dev/null 2>&1 || backup_die "Required command is unavailable: $1"
}

backup_now() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }
backup_timestamp() { date -u '+%Y%m%d_%H%M%S'; }

backup_file_size() {
  stat -c '%s' "$1" 2>/dev/null || stat -f '%z' "$1"
}

backup_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    shasum -a 256 "$1" | awk '{print $1}'
  fi
}

backup_check_sha256() {
  local file="$1" sidecar="${1}.sha256" expected actual
  [[ -s "$file" && -s "$sidecar" ]] || return 1
  expected="$(awk 'NR == 1 { print $1 }' "$sidecar")"
  actual="$(backup_sha256 "$file")"
  [[ -n "$expected" && "$expected" == "$actual" ]]
}

backup_write_json() {
  # Values are JSON strings. Callers must never pass credentials.
  local destination="$1"
  shift
  mkdir -p "$(dirname "$destination")"
  python3 - "$destination" "$@" <<'PY'
import json
import os
import sys
from pathlib import Path

destination = Path(sys.argv[1])
payload = {}
for argument in sys.argv[2:]:
    key, value = argument.split("=", 1)
    payload[key] = value
temporary = destination.with_suffix(destination.suffix + ".partial")
temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
os.chmod(temporary, 0o600)
temporary.replace(destination)
PY
}

backup_init_log() {
  local filename="$1"
  mkdir -p "$RAINBOW_BACKUP_LOG_DIR" "$RAINBOW_BACKUP_STATUS_DIR"
  chmod 700 "$RAINBOW_BACKUP_LOG_DIR" "$RAINBOW_BACKUP_STATUS_DIR"
  BACKUP_LOG_FILE="${RAINBOW_BACKUP_LOG_DIR}/${filename}"
  touch "$BACKUP_LOG_FILE"
  chmod 600 "$BACKUP_LOG_FILE"
}

backup_log() {
  printf '%s %s\n' "$(backup_now)" "$*" | tee -a "$BACKUP_LOG_FILE" >&2
}

backup_lock() {
  local name="$1"
  backup_require_command flock
  mkdir -p "${RAINBOW_BACKUP_ROOT}/.locks"
  chmod 700 "${RAINBOW_BACKUP_ROOT}/.locks"
  # shellcheck disable=SC3045
  exec 9>"${RAINBOW_BACKUP_ROOT}/.locks/${name}.lock"
  flock -n 9 || backup_die "Another ${name} operation is already running."
}

backup_load_backend_env() {
  [[ -r "$RAINBOW_BACKEND_ENV" ]] || backup_die "Missing protected backend environment file: $RAINBOW_BACKEND_ENV"
  # shellcheck disable=SC1090
  source "$RAINBOW_BACKEND_ENV"
  : "${POSTGRES_DB:?POSTGRES_DB is required in backend.env}"
  : "${POSTGRES_USER:?POSTGRES_USER is required in backend.env}"
}

backup_compose() {
  local -a project_arguments=()
  [[ -d "$RAINBOW_CURRENT_DIR" ]] || backup_die "Current release directory is missing: $RAINBOW_CURRENT_DIR"
  if [[ -n "${RAINBOW_COMPOSE_PROJECT:-}" ]]; then
    project_arguments=(--project-name "$RAINBOW_COMPOSE_PROJECT")
  fi
  (cd "$RAINBOW_CURRENT_DIR" && docker compose "${project_arguments[@]}" "$@")
}

backup_postgres_container() {
  local container candidate image
  container="$(backup_compose ps -q postgres 2>/dev/null || true)"
  if [[ -z "$container" ]]; then
    container="$(docker ps --filter 'label=com.docker.compose.service=postgres' --format '{{.ID}}' | head -n 1)"
  fi
  if [[ -z "$container" ]]; then
    while IFS= read -r candidate; do
      image="$(docker inspect -f '{{.Config.Image}}' "$candidate")"
      if [[ "$image" == postgres:* || "$image" == */postgres:* ]]; then
        container="$candidate"
        break
      fi
    done < <(backup_compose ps -q 2>/dev/null || true)
  fi
  [[ -n "$container" ]] || backup_die "No running PostgreSQL Compose container was detected."
  printf '%s\n' "$container"
}

backup_backend_container() {
  local container candidate upload_dir
  container="$(backup_compose ps -q backend 2>/dev/null || true)"
  if [[ -z "$container" ]]; then
    container="$(docker ps --filter 'label=com.docker.compose.service=backend' --format '{{.ID}}' | head -n 1)"
  fi
  if [[ -z "$container" ]]; then
    while IFS= read -r candidate; do
      upload_dir="$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$candidate" | sed -n 's/^UPLOAD_DIR=//p' | head -n 1)"
      if [[ -n "$upload_dir" ]]; then
        container="$candidate"
        break
      fi
    done < <(backup_compose ps -q 2>/dev/null || true)
  fi
  [[ -n "$container" ]] || backup_die "No running backend Compose container was detected."
  printf '%s\n' "$container"
}

backup_postgres_image() { docker inspect -f '{{.Config.Image}}' "$(backup_postgres_container)"; }
backup_compose_project() { docker inspect -f '{{ index .Config.Labels "com.docker.compose.project" }}' "$(backup_postgres_container)"; }
backup_deployed_commit() { git -C "$RAINBOW_CURRENT_DIR" rev-parse HEAD 2>/dev/null || printf 'unknown\n'; }

backup_upload_source() {
  local container source container_path mount_lines
  container="$(backup_backend_container)"
  if [[ "${UPLOAD_DIR:-app/uploads}" == /* ]]; then
    container_path="${UPLOAD_DIR}"
  else
    container_path="/app/${UPLOAD_DIR:-app/uploads}"
  fi
  mount_lines="$(docker inspect -f '{{range .Mounts}}{{printf "%s|%s\n" .Destination .Source}}{{end}}' "$container")"
  source="$(printf '%s\n' "$mount_lines" | awk -F'|' -v target="$container_path" '$1 == target { print $2; exit }')"
  [[ -n "$source" ]] || backup_die "The backend upload mount could not be detected at ${container_path}."
  [[ -d "$source" ]] || backup_die "The detected upload mount is not host-readable: ${source}. Configure a host bind mount before enabling host backups."
  printf '%s\n' "$source"
}

backup_redact_repository() {
  printf '%s' "$1" | sed -E 's#(://)[^/@]+@#\1[redacted]@#; s/[?].*/?[redacted]/'
}

backup_cleanup_partials() {
  find "$RAINBOW_BACKUP_ROOT" -xdev -type f -name '*.partial' -mmin +1440 -print -delete 2>/dev/null || true
}
