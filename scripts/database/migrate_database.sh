#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"
load_database_migration_config

require_remote_database_config
require_value REMOTE_BACKEND_SERVICE

remote_ssh bash -s -- "$REMOTE_APP_DIR" "$(remote_compose_file)" "$REMOTE_BACKEND_SERVICE" <<'REMOTE'
set -Eeuo pipefail
app_dir="$1"; compose_file="$2"; backend_service="$3"
cd "$app_dir"
compose=(docker compose)
[[ -n "$compose_file" ]] && compose+=( -f "$compose_file" )
"${compose[@]}" config --services | grep -Fx "$backend_service" >/dev/null
"${compose[@]}" run --rm "$backend_service" alembic upgrade heads
REMOTE
printf 'Remote Alembic migrations completed.\n'
