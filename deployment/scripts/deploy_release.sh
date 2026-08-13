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
"${compose[@]}" run --rm backend alembic upgrade head
test "$("${compose[@]}" run --rm backend alembic heads | grep -c '(head)')" -eq 1
"${compose[@]}" up -d --remove-orphans
"$script_dir/wait_for_application.sh" --base-url "$LOCAL_DEPLOY_URL" --timeout 180
"$script_dir/wait_for_application.sh" --base-url "$PUBLIC_DEPLOY_URL" --timeout 180
PUBLIC_BASE_URL="$PUBLIC_DEPLOY_URL" LOCAL_BASE_URL="$LOCAL_DEPLOY_URL" \
  HTTP_BASE_URL="${PUBLIC_DEPLOY_URL/https:/http:}" "$script_dir/smoke_test_production.sh"

trap - EXIT
printf 'deployment activation: PASS (%s)\n' "$DEPLOY_ENVIRONMENT"
