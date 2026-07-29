#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"
load_database_migration_config

expected_checksum=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --expected-checksum) expected_checksum="${2:-}"; shift 2 ;;
    *) printf 'Usage: %s [--expected-checksum <sha256>]\n' "$(basename "$0")" >&2; exit 2 ;;
  esac
done

require_remote_database_config
require_value REMOTE_BACKEND_SERVICE
remote_ssh bash -s -- "$REMOTE_APP_DIR" "$(remote_compose_file)" "$REMOTE_POSTGRES_SERVICE" "$REMOTE_DATABASE_NAME" "$REMOTE_DATABASE_USER" "$REMOTE_BACKEND_SERVICE" "${REMOTE_STAGED_DUMP_PATH:-}" "$expected_checksum" <<'REMOTE'
set -Eeuo pipefail
app_dir="$1"; compose_file="$2"; pg_service="$3"; database="$4"; user="$5"; backend_service="$6"; staged_dump="$7"; expected_checksum="$8"
cd "$app_dir"
compose=(docker compose)
[[ -n "$compose_file" ]] && compose+=( -f "$compose_file" )
"${compose[@]}" exec -T "$pg_service" psql -U "$user" -d "$database" -v ON_ERROR_STOP=1 -tAc 'select 1' | grep -qx 1
"${compose[@]}" exec -T "$pg_service" psql -U "$user" -d "$database" -tAc "select to_regclass('public.alembic_version')" | grep -qx alembic_version
"${compose[@]}" ps "$backend_service" --status running >/dev/null
if [[ -n "$expected_checksum" ]]; then
  test -s "$staged_dump"
  if command -v sha256sum >/dev/null 2>&1; then
    actual_checksum="$(sha256sum "$staged_dump" | awk '{print $1}')"
  else
    actual_checksum="$(shasum -a 256 "$staged_dump" | awk '{print $1}')"
  fi
  [[ "$actual_checksum" == "$expected_checksum" ]] || { printf 'Staged dump checksum no longer matches.\n' >&2; exit 1; }
fi
printf 'Remote database connection, Alembic table, and backend service verified.\n'
REMOTE

if [[ -n "${REMOTE_HEALTH_URL:-}" ]]; then
  require_command curl
  curl --fail --silent --show-error --max-time 15 "$REMOTE_HEALTH_URL" >/dev/null
  printf 'Remote health endpoint verified.\n'
else
  printf 'Remote health endpoint skipped: REMOTE_HEALTH_URL is not configured.\n'
fi
