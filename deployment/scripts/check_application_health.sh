#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/opt/rainbow-fashions-prod/current}"
STATE_DIR="${STATE_DIR:-/opt/rainbow-fashions-prod/monitoring/state}"
LOG_FILE="${LOG_FILE:-/var/log/rainbow-fashions/health-watch.log}"
ALERT_ENV_FILE="${ALERT_ENV_FILE:-/opt/rainbow-fashions-prod/shared/availability-alerts.env}"
LOCAL_BASE_URL="${LOCAL_BASE_URL:-http://127.0.0.1:8080}"
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-https://rainbow-fashions.in}"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-rainbow_prod}"
COMPOSE_OVERRIDE="${COMPOSE_OVERRIDE:-docker-compose.prod.yml}"
ROOT_DISK_WARN_PERCENT="${ROOT_DISK_WARN_PERCENT:-85}"
CERT_WARN_DAYS="${CERT_WARN_DAYS:-14}"
RESTART_COOLDOWN_SECONDS="${RESTART_COOLDOWN_SECONDS:-900}"

mkdir -p "$STATE_DIR" "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"

compose() {
  docker compose -p "$COMPOSE_PROJECT_NAME" -f docker-compose.yml -f "$COMPOSE_OVERRIDE" "$@"
}

log() {
  printf '%s health-watch %s\n' "$(date --iso-8601=seconds 2>/dev/null || date)" "$*" | tee -a "$LOG_FILE" >&2
}

load_alert_env() {
  if [[ -f "$ALERT_ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    . "$ALERT_ENV_FILE"
    set +a
  fi
}

send_alert() {
  local check="$1" result="$2" recovery="${3:-not_attempted}"
  load_alert_env
  [[ -n "${AVAILABILITY_WEBHOOK_URL:-}" ]] || return 0
  local payload
  payload="$(printf '{"hostname":"%s","environment":"%s","time":"%s","failed_check":"%s","result":"%s","recovery_attempted":"%s"}' \
    "$(hostname)" "${APP_ENVIRONMENT:-production}" "$(date --iso-8601=seconds 2>/dev/null || date)" "$check" "$result" "$recovery")"
  curl --silent --show-error --fail --connect-timeout 5 --max-time 10 \
    -H 'Content-Type: application/json' \
    -d "$payload" \
    "$AVAILABILITY_WEBHOOK_URL" >/dev/null || true
}

check_service_active() {
  local service="$1"
  systemctl is-active --quiet "$service"
}

check_url() {
  local url="$1"
  [[ "$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' --connect-timeout 5 --max-time 10 "$url" || true)" == "200" ]]
}

attempt_recovery_once() {
  local now last
  now="$(date +%s)"
  last="$(cat "$STATE_DIR/last-restart-at" 2>/dev/null || echo 0)"
  if (( now - last < RESTART_COOLDOWN_SECONDS )); then
    log "Recovery suppressed by cooldown."
    return 1
  fi
  echo "$now" > "$STATE_DIR/last-restart-at"
  log "Attempting controlled docker compose up -d recovery."
  (cd "$APP_DIR" && compose logs --tail=200 --no-color > "$STATE_DIR/container-logs-before-recovery.log" 2>&1 || true)
  (cd "$APP_DIR" && compose up -d)
}

failures=()

check_service_active docker || failures+=("docker_stopped")
check_service_active nginx || failures+=("nginx_stopped")

if [[ -d "$APP_DIR" ]]; then
  if ! (cd "$APP_DIR" && compose ps --services --filter status=running | grep -q .); then
    failures+=("containers_not_running")
  fi
  unhealthy="$(cd "$APP_DIR" && docker inspect -f '{{.Name}} {{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' $(compose ps -q) 2>/dev/null | awk '$2=="unhealthy"{print $1}' || true)"
  [[ -z "$unhealthy" ]] || failures+=("container_unhealthy")
else
  failures+=("app_dir_missing")
fi

check_url "${LOCAL_BASE_URL%/}/health/ready" || failures+=("local_readiness_failed")
check_url "${PUBLIC_BASE_URL%/}/health/ready" || failures+=("public_readiness_failed")

root_used="$(df -P / | awk 'NR==2 {gsub("%","",$5); print $5}')"
if [[ "$root_used" =~ ^[0-9]+$ ]] && (( root_used >= ROOT_DISK_WARN_PERCENT )); then
  failures+=("root_disk_${root_used}_percent")
fi

docker_used="$(docker system df --format '{{.Size}}' 2>/dev/null | head -n 1 || true)"
log "Docker disk usage summary: ${docker_used:-unavailable}"

public_host="${PUBLIC_BASE_URL#https://}"
public_host="${public_host%%/*}"
if [[ -n "$public_host" ]]; then
  if ! echo | openssl s_client -connect "${public_host}:443" -servername "$public_host" 2>/dev/null | openssl x509 -checkend "$((CERT_WARN_DAYS * 86400))" -noout >/dev/null 2>&1; then
    failures+=("certificate_expiring_or_invalid")
  fi
fi

if (( ${#failures[@]} == 0 )); then
  echo "ok" > "$STATE_DIR/latest-status"
  log "All health checks passed."
  exit 0
fi

log "Health failures: ${failures[*]}"
recovery_result="not_attempted"
if printf '%s\n' "${failures[@]}" | grep -Eq 'container|local_readiness'; then
  if attempt_recovery_once && check_url "${LOCAL_BASE_URL%/}/health/ready" && check_url "${PUBLIC_BASE_URL%/}/health/ready"; then
    recovery_result="recovered"
    echo "recovered" > "$STATE_DIR/latest-status"
    log "Recovery succeeded."
    exit 0
  fi
  recovery_result="failed"
fi

echo "failed:${failures[*]}" > "$STATE_DIR/latest-status"
send_alert "${failures[*]}" "failed" "$recovery_result"
exit 1
