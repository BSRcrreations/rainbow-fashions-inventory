#!/usr/bin/env bash
set -Eeuo pipefail

BASE_URL=""
TIMEOUT_SECONDS=180

usage() {
  echo "Usage: $0 --base-url URL [--timeout SECONDS]" >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url) BASE_URL="${2:-}"; shift 2 ;;
    --timeout) TIMEOUT_SECONDS="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) usage; exit 2 ;;
  esac
done

[[ -n "$BASE_URL" ]] || { usage; exit 2; }
[[ "$TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || { echo "Timeout must be seconds." >&2; exit 2; }

deadline=$((SECONDS + TIMEOUT_SECONDS))
attempt=0
curl_error_file="$(mktemp /tmp/rainbow-wait-curl.XXXXXX)"
trap 'rm -f "$curl_error_file"' EXIT

check_path() {
  local path="$1"
  local url="${BASE_URL%/}${path}"
  local started status duration
  started="$(date +%s)"
  status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' --connect-timeout 5 --max-time 10 "$url" 2>"$curl_error_file" || true)"
  duration=$(( $(date +%s) - started ))
  printf 'wait_for_application attempt=%s url=%s status=%s duration=%ss\n' "$attempt" "$url" "${status:-000}" "$duration"
  [[ "$status" == "200" ]]
}

while (( SECONDS < deadline )); do
  attempt=$((attempt + 1))
  if check_path "/health/live" && check_path "/health/ready"; then
    echo "Application is healthy at $BASE_URL"
    exit 0
  fi
  sleep 5
done

echo "Application did not become healthy at $BASE_URL within ${TIMEOUT_SECONDS}s." >&2
if [[ "$BASE_URL" == http://127.0.0.1:* || "$BASE_URL" == http://localhost:* ]]; then
  docker compose ps >&2 || true
fi
exit 1
