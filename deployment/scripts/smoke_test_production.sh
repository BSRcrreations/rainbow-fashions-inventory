#!/usr/bin/env bash
set -Eeuo pipefail

LOCAL_BASE_URL="${LOCAL_BASE_URL:-http://127.0.0.1:8080}"
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-https://test.rainbow-fashions.in}"
HTTP_BASE_URL="${HTTP_BASE_URL:-http://test.rainbow-fashions.in}"

curl_common=(--fail --show-error --location --connect-timeout 5 --max-time 20)

check_html() {
  local base_url="$1"
  local body
  body="$(curl "${curl_common[@]}" "${base_url%/}/")"
  printf '%s' "$body" | grep -qi '<html'
}

check_health() {
  local base_url="$1"
  curl "${curl_common[@]}" "${base_url%/}/health/live" >/dev/null
  curl "${curl_common[@]}" "${base_url%/}/health/ready" >/dev/null
}

check_api_routing() {
  local base_url="$1"
  local status
  status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' --connect-timeout 5 --max-time 20 "${base_url%/}/api/v1/auth/me")"
  [[ "$status" == "401" || "$status" == "403" ]]
}

check_static_asset() {
  local base_url="$1"
  local asset
  asset="$(curl "${curl_common[@]}" "${base_url%/}/" | grep -Eo '/assets/[^"]+\.js' | head -n 1 || true)"
  [[ -n "$asset" ]] || return 1
  curl "${curl_common[@]}" "${base_url%/}${asset}" >/dev/null
}

check_upload_route() {
  local base_url="$1"
  local status
  status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' --connect-timeout 5 --max-time 20 "${base_url%/}/uploads/products/__smoke_missing__")"
  [[ "$status" == "404" || "$status" == "403" ]]
}

echo "Running local smoke tests at $LOCAL_BASE_URL"
check_html "$LOCAL_BASE_URL"
check_health "$LOCAL_BASE_URL"
check_api_routing "$LOCAL_BASE_URL"
check_static_asset "$LOCAL_BASE_URL"
check_upload_route "$LOCAL_BASE_URL"

echo "Running public smoke tests at $PUBLIC_BASE_URL"
check_html "$PUBLIC_BASE_URL"
check_health "$PUBLIC_BASE_URL"
check_api_routing "$PUBLIC_BASE_URL"
check_static_asset "$PUBLIC_BASE_URL"
check_upload_route "$PUBLIC_BASE_URL"

echo "Checking HTTP redirect at $HTTP_BASE_URL"
redirect_status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code} %{redirect_url}' --connect-timeout 5 --max-time 20 "$HTTP_BASE_URL")"
case "$redirect_status" in
  301\ https://*|308\ https://*) ;;
  *) echo "Expected HTTP redirect to HTTPS, got: $redirect_status" >&2; exit 1 ;;
esac

host="${PUBLIC_BASE_URL#https://}"
host="${host%%/*}"
echo | openssl s_client -connect "${host}:443" -servername "$host" >/tmp/rainbow-smoke-cert.txt 2>/dev/null
grep -q "BEGIN CERTIFICATE" /tmp/rainbow-smoke-cert.txt

echo "Production smoke tests passed."
