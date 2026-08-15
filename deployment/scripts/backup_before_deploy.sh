#!/usr/bin/env bash
# Create a non-empty PostgreSQL backup of the environment being deployed.  It
# never discovers a container globally: the explicit Compose project prevents
# test jobs from selecting production PostgreSQL by mistake.
set -Eeuo pipefail

: "${DEPLOY_PATH:?DEPLOY_PATH is required}"
: "${COMPOSE_PROJECT_NAME:?COMPOSE_PROJECT_NAME is required}"
: "${COMPOSE_OVERRIDE:?COMPOSE_OVERRIDE is required}"
: "${DEPLOY_ENVIRONMENT:?DEPLOY_ENVIRONMENT is required}"
: "${CI_COMMIT_SHORT_SHA:?CI_COMMIT_SHORT_SHA is required}"

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$script_dir/verify_deployment_context.sh"

current="$DEPLOY_PATH/current"
if [[ ! -d "$current" ]]; then
  if [[ "$DEPLOY_ENVIRONMENT" == test ]]; then
    echo 'pre-deployment backup: no prior test release; initial test deployment may continue'
    exit 0
  fi
  echo 'pre-deployment backup: production has no active release to back up' >&2
  exit 1
fi

backup_dir="$DEPLOY_PATH/backups"
install -d -m 700 "$backup_dir"
backup_file="$backup_dir/postgres_${DEPLOY_ENVIRONMENT}_${CI_COMMIT_SHORT_SHA}_$(date -u +%Y%m%d_%H%M%S).dump"
compose=(docker compose -p "$COMPOSE_PROJECT_NAME" -f "$current/docker-compose.yml" -f "$current/$COMPOSE_OVERRIDE")

"${compose[@]}" ps postgres >/dev/null
"${compose[@]}" exec -T postgres sh -ec 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom' > "$backup_file"
if [[ ! -s "$backup_file" ]]; then
  rm -f "$backup_file"
  echo 'pre-deployment backup: backup file was empty' >&2
  exit 1
fi
chmod 600 "$backup_file"
echo 'pre-deployment backup: PASS'
