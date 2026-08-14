#!/usr/bin/env bash
# Activate a release only after the CI job has created a verified backup.  This
# script is intentionally environment-agnostic, but refuses cross-environment
# paths and Compose project names through verify_deployment_context.sh.
set -Eeuo pipefail

: "${RELEASE_DIR:?RELEASE_DIR is required}"
: "${COMPOSE_OVERRIDE:?COMPOSE_OVERRIDE is required}"
: "${LOCAL_DEPLOY_URL:?LOCAL_DEPLOY_URL is required}"
: "${PUBLIC_DEPLOY_URL:?PUBLIC_DEPLOY_URL is required}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$script_dir/verify_deployment_context.sh"

[[ -d "$RELEASE_DIR" ]] || { echo 'deployment activation: release directory is missing' >&2; exit 1; }
[[ "$RELEASE_DIR" == "$DEPLOY_PATH/releases/"* ]] || { echo 'deployment activation: release is outside the deployment root' >&2; exit 1; }
[[ -f "$RELEASE_DIR/$COMPOSE_OVERRIDE" ]] || { echo 'deployment activation: environment Compose override is missing' >&2; exit 1; }

compose=(docker compose -p "$COMPOSE_PROJECT_NAME" -f docker-compose.yml -f "$COMPOSE_OVERRIDE")
previous_release=""
if [[ -L "$DEPLOY_PATH/current" ]]; then previous_release="$(readlink -f "$DEPLOY_PATH/current")"; fi

rollback() {
  status=$?
  [[ "$status" -eq 0 ]] && return 0
  echo 'deployment activation failed; restoring the previous application release when available' >&2
  if [[ -n "$previous_release" && -d "$previous_release" ]]; then
    ln -sfn "$previous_release" "$DEPLOY_PATH/current"
    (
      cd "$previous_release"
      "${compose[@]}" up -d || true
    )
  fi
  exit "$status"
}
trap rollback EXIT

ln -sfn "$RELEASE_DIR" "$DEPLOY_PATH/current"
cd "$RELEASE_DIR"

# Values are read by Docker Compose directly from the protected file; this
# avoids copying a secret-bearing .env into the release artifact.
"${compose[@]}" config --quiet
"${compose[@]}" build
"${compose[@]}" up -d postgres

# The historical Alembic chain begins with a change to an already-existing
# legacy schema. A brand-new, isolated TEST database therefore cannot replay
# that chain from revision zero. Bootstrap only an empty database from the
# current SQLAlchemy metadata and stamp it at the single Alembic head. Never
# use this path for a database that already contains application tables.
schema_state="$("${compose[@]}" exec -T postgres sh -ec 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT CASE WHEN EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = '\''public'\'' AND tablename <> '\''alembic_version'\'') THEN '\''nonempty'\'' ELSE '\''empty'\'' END, CASE WHEN to_regclass('\''public.alembic_version'\'') IS NULL THEN '\''unstamped'\'' ELSE '\''stamped'\'' END"')"
case "$schema_state" in
  empty\|*)
    echo 'deployment activation: bootstrapping empty isolated database at the Alembic head'
    "${compose[@]}" run --rm -e RUN_MIGRATIONS_ON_STARTUP=false backend python -c 'from app import models; from app.database.base import Base; from app.database.session import engine; Base.metadata.create_all(bind=engine)'
    "${compose[@]}" run --rm -e RUN_MIGRATIONS_ON_STARTUP=false backend alembic stamp head
    ;;
  nonempty\|unstamped)
    echo 'deployment activation: legacy database contains application tables but has no Alembic version; a separate reviewed baseline is required' >&2
    exit 1
    ;;
  nonempty\|stamped)
    "${compose[@]}" run --rm -e RUN_MIGRATIONS_ON_STARTUP=false backend alembic upgrade head
    ;;
  *)
    echo 'deployment activation: could not determine database migration state' >&2
    exit 1
    ;;
esac
test "$("${compose[@]}" run --rm -e RUN_MIGRATIONS_ON_STARTUP=false backend alembic heads | grep -c '(head)')" -eq 1
"${compose[@]}" up -d --remove-orphans
# A first TEST build can spend several minutes applying the isolated schema and
# starting cold containers.  Production retains the existing three-minute
# guard; TEST gets a longer bounded readiness window without altering it.
local_health_timeout=180
if [[ "$DEPLOY_ENVIRONMENT" == test ]]; then
  local_health_timeout=360
fi
"$script_dir/wait_for_application.sh" --base-url "$LOCAL_DEPLOY_URL" --timeout "$local_health_timeout"

# TEST is activated behind a deliberately closed Nginx vhost. Its public
# proxy and certificate are configured only after loopback health succeeds,
# so public HTTPS verification is deferred to the TEST proxy/TLS phase.
if [[ "$DEPLOY_ENVIRONMENT" == production ]]; then
  "$script_dir/wait_for_application.sh" --base-url "$PUBLIC_DEPLOY_URL" --timeout 180
  PUBLIC_BASE_URL="$PUBLIC_DEPLOY_URL" LOCAL_BASE_URL="$LOCAL_DEPLOY_URL" \
    HTTP_BASE_URL="${PUBLIC_DEPLOY_URL/https:/http:}" "$script_dir/smoke_test_production.sh"
else
  echo 'test activation: loopback health passed; public verification is deferred to the TEST proxy/TLS phase'
fi

trap - EXIT
printf 'deployment activation: PASS (%s)\n' "$DEPLOY_ENVIRONMENT"
