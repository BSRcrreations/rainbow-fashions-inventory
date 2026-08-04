#!/usr/bin/env bash
# Verify the production shell-runner host without printing runtime configuration.
set -Eeuo pipefail

deploy_path="${DEPLOY_PATH:-/opt/rainbow-fashions}"
environment_file="$deploy_path/shared/backend.env"
deployment_user="${DEPLOYMENT_USER:-$(id -un)}"
failed=0

fail() {
  printf 'production runner preflight: %s\n' "$1" >&2
  failed=1
}

for command in bash curl openssl docker nginx certbot gitlab-runner df; do
  command -v "$command" >/dev/null 2>&1 || fail "required command missing: $command"
done
docker compose version >/dev/null 2>&1 || fail 'Docker Compose plugin is unavailable'

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
  for origin in https://test.rainbow-fashions.in https://rainbow-fashions.in https://www.rainbow-fashions.in; do
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
