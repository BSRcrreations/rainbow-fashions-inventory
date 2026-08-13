#!/usr/bin/env bash
# Verify the production shell-runner host without printing runtime configuration.
set -Eeuo pipefail

deploy_path="${DEPLOY_PATH:-/opt/rainbow-fashions-prod}"
environment_file="$deploy_path/shared/backend.env"
deployment_user="${DEPLOYMENT_USER:-$(id -un)}"
production_runner_marker="/etc/rainbow-fashions-production-runner"
failed=0

fail() {
  printf 'production runner preflight: %s\n' "$1" >&2
  failed=1
}

if [[ ! -f "$production_runner_marker" ]] || ! grep -Fxq 'RAINBOW_PRODUCTION_RUNNER=1' "$production_runner_marker"; then
  printf 'production runner preflight: this job is not running on the approved production shell runner\n' >&2
  exit 1
fi

marker_mode="$(stat -c '%a' "$production_runner_marker")"
marker_owner="$(stat -c '%U' "$production_runner_marker")"
[[ "$marker_mode" == "644" ]] || fail 'production runner marker mode must be 644'
[[ "$marker_owner" == "root" ]] || fail 'production runner marker must be root-owned'

[[ -d /run/systemd/system ]] || fail 'systemd host environment is unavailable'

for command in bash curl openssl docker nginx certbot gitlab-runner df; do
  command -v "$command" >/dev/null 2>&1 || fail "required command missing: $command"
done

command -v systemctl >/dev/null 2>&1 || fail 'systemctl is unavailable'
for service in gitlab-runner docker nginx; do
  systemctl is-active --quiet "$service" || fail "required host service is not active: $service"
done

[[ -S /var/run/docker.sock ]] || fail 'host Docker socket is unavailable'
docker compose version >/dev/null 2>&1 || fail 'Docker Compose plugin is unavailable'
docker info >/dev/null 2>&1 || fail 'Docker daemon is unavailable to the runner user'

[[ -d "$deploy_path" ]] || fail "required deployment root missing: $deploy_path"
[[ -r "$deploy_path" && -x "$deploy_path" ]] || fail "runner user cannot access deployment root: $deploy_path"

for directory in \
  "$deploy_path/releases" \
  "$deploy_path/shared" \
  "$deploy_path/backups" \
  "$deploy_path/runtime/uploads" \
  "$deploy_path/runtime/opening-stock-imports" \
  "$deploy_path/runtime/backups/status"; do
  [[ -d "$directory" ]] || fail "required directory missing: $directory"
done

[[ -s "$environment_file" ]] || fail 'production environment file is missing or empty'
if [[ -s "$environment_file" ]]; then
  mode="$(stat -c '%a' "$environment_file")"
  owner="$(stat -c '%U' "$environment_file")"
  [[ "$mode" == "600" ]] || fail 'production environment file mode must be 600'
  [[ "$owner" == "$deployment_user" ]] || fail 'production environment file owner does not match DEPLOYMENT_USER'
  grep -q '^APP_ENV=production$' "$environment_file" || fail 'production APP_ENV is not configured'
  grep -q '^DEBUG=false$' "$environment_file" || fail 'production DEBUG is not configured'
  awk -F= '$1 == "POSTGRES_PASSWORD" { found=1; if (length($2) < 32) exit 1 } END { exit found ? 0 : 1 }' "$environment_file" || fail 'PostgreSQL password does not meet the minimum length policy'
  awk -F= '$1 == "JWT_SECRET_KEY" { found=1; if (length($2) < 64) exit 1 } END { exit found ? 0 : 1 }' "$environment_file" || fail 'JWT secret does not meet the minimum length policy'
  for origin in https://rainbow-fashions.in https://www.rainbow-fashions.in; do
    grep -Fq "$origin" "$environment_file" || fail "required CORS origin missing: $origin"
  done
  if grep -Ev '^[[:space:]]*(#|$)' "$environment_file" | grep -Eqi 'replace-this|change-me|example'; then
    fail 'production environment file contains a placeholder'
  fi
fi

available_kb="$(df -Pk "$deploy_path" | awk 'NR == 2 { print $4 }')"
[[ "${available_kb:-0}" =~ ^[0-9]+$ ]] && (( available_kb >= 5242880 )) || fail 'less than 5 GiB is available for deployment and rollback'

if (( failed )); then
  exit 1
fi

printf 'production runner preflight: passed\n'
