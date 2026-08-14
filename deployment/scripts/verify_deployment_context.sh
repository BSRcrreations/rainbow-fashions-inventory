#!/usr/bin/env bash
# Verify a deployment runner and its isolated environment without displaying
# protected environment-file contents or credentials.
set -Eeuo pipefail

: "${DEPLOY_ENVIRONMENT:?DEPLOY_ENVIRONMENT must be test or production}"
: "${DEPLOY_PATH:?DEPLOY_PATH is required}"
: "${COMPOSE_PROJECT_NAME:?COMPOSE_PROJECT_NAME is required}"
: "${BACKEND_ENV_FILE:?BACKEND_ENV_FILE is required}"

case "$DEPLOY_ENVIRONMENT" in
  test)
    expected_path=/opt/rainbow-fashions-test
    expected_project=rainbow_test
    expected_marker=/etc/rainbow-fashions-test-runner
    expected_marker_value=RAINBOW_TEST_RUNNER=1
    expected_tag=rainbow-test
    expected_origin=https://test.rainbow-fashions.in
    ;;
  production)
    expected_path=/opt/rainbow-fashions-prod
    expected_project=rainbow_prod
    expected_marker=/etc/rainbow-fashions-production-runner
    expected_marker_value=RAINBOW_PRODUCTION_RUNNER=1
    expected_tag=rainbow-production
    expected_origin=https://rainbow-fashions.in
    ;;
  *) echo 'deployment preflight: unsupported environment' >&2; exit 2 ;;
esac

fail() { printf 'deployment preflight: %s\n' "$1" >&2; exit 1; }

[[ "$DEPLOY_PATH" == "$expected_path" ]] || fail 'deployment path does not match the requested environment'
[[ "$COMPOSE_PROJECT_NAME" == "$expected_project" ]] || fail 'Compose project does not match the requested environment'
[[ "$BACKEND_ENV_FILE" == "$DEPLOY_PATH/shared/backend.env" ]] || fail 'environment file is outside the requested deployment root'
[[ -f "$expected_marker" ]] && grep -Fxq "$expected_marker_value" "$expected_marker" || fail 'approved deployment-runner marker is missing'
[[ "$(stat -c '%a' "$expected_marker")" == 644 ]] || fail 'deployment-runner marker mode must be 644'
[[ "$(stat -c '%U' "$expected_marker")" == root ]] || fail 'deployment-runner marker must be root-owned'

if [[ -n "${CI_RUNNER_TAGS:-}" ]] && [[ ",${CI_RUNNER_TAGS// /}," != *",${expected_tag},"* ]]; then
  fail 'runner does not have the required environment tag'
fi

for command in docker gitlab-runner nginx curl openssl; do
  command -v "$command" >/dev/null 2>&1 || fail "required command is unavailable: $command"
done
for service in docker gitlab-runner nginx; do
  systemctl is-active --quiet "$service" || fail "required service is inactive: $service"
done
docker compose version >/dev/null 2>&1 || fail 'Docker Compose plugin is unavailable'
docker info >/dev/null 2>&1 || fail 'Docker daemon is unavailable to the runner user'

for directory in "$DEPLOY_PATH" "$DEPLOY_PATH/releases" "$DEPLOY_PATH/shared" \
  "$DEPLOY_PATH/backups" "$DEPLOY_PATH/runtime/uploads" \
  "$DEPLOY_PATH/runtime/opening-stock-imports" "$DEPLOY_PATH/runtime/backups/status"; do
  [[ -d "$directory" ]] || fail 'required deployment directory is missing'
done
for directory in "$DEPLOY_PATH" "$DEPLOY_PATH/releases" "$DEPLOY_PATH/backups"; do
  [[ -w "$directory" ]] || fail 'runner cannot write a required deployment directory'
done

[[ -s "$BACKEND_ENV_FILE" ]] || fail 'environment file is missing or empty'
[[ "$(stat -c '%a' "$BACKEND_ENV_FILE")" == 600 ]] || fail 'environment file mode must be 600'

required_names=(APP_ENV DEBUG POSTGRES_DB POSTGRES_USER POSTGRES_PASSWORD DATABASE_URL JWT_SECRET_KEY CORS_ORIGINS)
for name in "${required_names[@]}"; do
  grep -Eq "^[[:space:]]*${name}=" "$BACKEND_ENV_FILE" || fail "required environment variable is missing: ${name}"
done
grep -Eq '^[[:space:]]*DEBUG=false[[:space:]]*$' "$BACKEND_ENV_FILE" || fail 'DEBUG must be false'
if [[ "$DEPLOY_ENVIRONMENT" == production ]]; then
  grep -Eq '^[[:space:]]*APP_ENV=production[[:space:]]*$' "$BACKEND_ENV_FILE" || fail 'APP_ENV must be production'
  grep -Fq 'https://www.rainbow-fashions.in' "$BACKEND_ENV_FILE" || fail 'production CORS origin is missing'
else
  grep -Eq '^[[:space:]]*APP_ENV=(test|staging)[[:space:]]*$' "$BACKEND_ENV_FILE" || fail 'test APP_ENV must be test or staging'
fi
grep -Fq "$expected_origin" "$BACKEND_ENV_FILE" || fail 'required CORS origin is missing'
awk -F= '$1 == "JWT_SECRET_KEY" { found=1; if (length($2) < 64) exit 1 } END { exit found ? 0 : 1 }' "$BACKEND_ENV_FILE" || fail 'JWT secret does not meet the minimum length policy'
if grep -Ev '^[[:space:]]*(#|$)' "$BACKEND_ENV_FILE" | grep -Eqi 'replace-this|change-me|example'; then
  fail 'environment file contains a placeholder'
fi

printf 'deployment preflight: PASS (%s)\n' "$DEPLOY_ENVIRONMENT"
