#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DOMAIN="${ROOT_DOMAIN:-rainbow-fashions.in}"
APP_DOMAIN="${APP_DOMAIN:-test.rainbow-fashions.in}"
EXPECTED_IPV4="${EXPECTED_IPV4:-178.238.237.182}"
EXPECTED_NAMESERVERS="${EXPECTED_NAMESERVERS:-}"
HTTP_TIMEOUT_SECONDS="${HTTP_TIMEOUT_SECONDS:-8}"
REPORT_FILE="${REPORT_FILE:-}"

STATE="UNKNOWN"
FAILURE_DETAIL=""

log_lines=()

emit() {
  local line="$*"
  log_lines+=("$line")
  printf '%s\n' "$line"
}

finish() {
  local code="$1"
  if [[ -n "$REPORT_FILE" ]]; then
    mkdir -p "$(dirname "$REPORT_FILE")"
    printf '%s\n' "${log_lines[@]}" > "$REPORT_FILE"
  fi
  exit "$code"
}

join_by_comma() {
  local IFS=","
  printf '%s' "$*"
}

normalize_list() {
  tr '[:upper:]' '[:lower:]' | sed 's/\.$//' | sed '/^[[:space:]]*$/d' | sort -u
}

has_command() {
  command -v "$1" >/dev/null 2>&1
}

dig_short() {
  local args=("$@")
  if has_command dig; then
    dig +short "${args[@]}" 2>/dev/null | sed '/^[[:space:]]*$/d' || true
  fi
}

dig_trace() {
  if has_command dig; then
    dig +trace "$APP_DOMAIN" 2>/dev/null | tail -40 || true
  fi
}

curl_status() {
  local url="$1"
  if has_command curl; then
    curl --silent --show-error --output /tmp/rainbow-domain-http-body --write-out '%{http_code}' --connect-timeout "$HTTP_TIMEOUT_SECONDS" --max-time "$HTTP_TIMEOUT_SECONDS" "$url" 2>/tmp/rainbow-domain-curl-error || true
  fi
}

rdap_lookup() {
  if has_command curl; then
    curl --silent --show-error --location --connect-timeout "$HTTP_TIMEOUT_SECONDS" --max-time "$HTTP_TIMEOUT_SECONDS" "https://rdap.org/domain/${ROOT_DOMAIN}" 2>/tmp/rainbow-domain-rdap-error || true
  fi
}

extract_json_value() {
  local key="$1"
  python3 -c '
import json
import sys
key = sys.argv[1]
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
value = data.get(key)
if isinstance(value, str):
    print(value)
elif isinstance(value, list):
    for item in value:
        if isinstance(item, str):
            print(item)
' "$key" 2>/dev/null || true
}

print_manual_dns_instructions() {
  emit ""
  emit "Registrar action required."
  emit "Configure authoritative nameservers for:"
  emit ""
  emit "$ROOT_DOMAIN"
  emit ""
  emit "Either:"
  emit ""
  emit "A. Use Cloudflare-assigned nameservers and update them at the registrar."
  emit ""
  emit "Or:"
  emit ""
  emit "B. Enable the registrar's default DNS nameservers."
  emit ""
  emit "After delegation, add:"
  emit ""
  emit "Type: A"
  emit "Name: test"
  emit "Value: $EXPECTED_IPV4"
  emit "TTL: 300 or Auto"
  emit ""
  emit "Do not attempt to modify DNS automatically."
}

emit "Rainbow Fashions domain diagnostic"
emit "root_domain=$ROOT_DOMAIN"
emit "app_domain=$APP_DOMAIN"
emit "expected_ipv4=$EXPECTED_IPV4"

whois_status=""
whois_registrar=""
if has_command whois; then
  whois_output="$(whois "$ROOT_DOMAIN" 2>/tmp/rainbow-domain-whois-error || true)"
  whois_status="$(printf '%s\n' "$whois_output" | awk -F: 'tolower($1) ~ /status/ {gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2}' | head -5 | paste -sd ',' -)"
  whois_registrar="$(printf '%s\n' "$whois_output" | awk -F: 'tolower($1) ~ /^registrar$/ {gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}')"
  if printf '%s\n' "$whois_output" | grep -Eiq 'no match|not found|no data found|domain not found|object does not exist'; then
    STATE="DOMAIN_NOT_REGISTERED"
  fi
else
  emit "whois=unavailable"
fi

rdap_body="$(rdap_lookup)"
rdap_status="$(printf '%s' "$rdap_body" | extract_json_value status | paste -sd ',' -)"
rdap_registrar="$(printf '%s' "$rdap_body" | python3 -c '
import json
import sys
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for entity in data.get("entities", []):
    roles = entity.get("roles", [])
    if "registrar" in roles:
        vcard = entity.get("vcardArray", [None, []])[1]
        for row in vcard:
            if row and row[0] == "fn":
                print(row[3])
                raise SystemExit
' 2>/dev/null || true
)"

if [[ "$rdap_body" == *'"errorCode":404'* || "$rdap_body" == *'"DOMAIN NOT FOUND"'* ]]; then
  STATE="DOMAIN_NOT_REGISTERED"
fi

combined_status="$(printf '%s,%s' "$whois_status" "$rdap_status" | tr '[:upper:]' '[:lower:]')"
if [[ "$combined_status" =~ clienthold|serverhold|inactive ]]; then
  STATE="DOMAIN_ON_HOLD"
fi

emit "registration_state=${STATE:-UNKNOWN}"
emit "registrar=${rdap_registrar:-${whois_registrar:-unknown}}"
emit "domain_status=${rdap_status:-${whois_status:-unknown}}"

root_ns="$(dig_short NS "$ROOT_DOMAIN" | normalize_list)"
soa="$(dig_short SOA "$ROOT_DOMAIN" | paste -sd ' ' -)"
emit "root_nameservers=$(printf '%s\n' "$root_ns" | paste -sd ',' -)"
emit "soa=${soa:-missing}"

if [[ "$STATE" == "DOMAIN_NOT_REGISTERED" || "$STATE" == "DOMAIN_ON_HOLD" ]]; then
  emit "state=$STATE"
  finish 1
fi

if [[ -z "$root_ns" ]]; then
  STATE="NO_NAMESERVER_DELEGATION"
  emit "state=$STATE"
  print_manual_dns_instructions
  finish 1
fi

if [[ -n "$EXPECTED_NAMESERVERS" ]]; then
  expected_ns="$(printf '%s\n' "$EXPECTED_NAMESERVERS" | tr ',' '\n' | normalize_list)"
  if [[ "$root_ns" != "$expected_ns" ]]; then
    STATE="NAMESERVER_MISMATCH"
    emit "state=$STATE"
    emit "expected_nameservers=$(printf '%s\n' "$expected_ns" | paste -sd ',' -)"
    finish 1
  fi
fi

system_a="$(dig_short A "$APP_DOMAIN" | normalize_list)"
system_aaaa="$(dig_short AAAA "$APP_DOMAIN" | normalize_list)"
cname="$(dig_short CNAME "$APP_DOMAIN" | normalize_list)"
resolver_1111="$(dig_short @1.1.1.1 A "$APP_DOMAIN" | normalize_list)"
resolver_8888="$(dig_short @8.8.8.8 A "$APP_DOMAIN" | normalize_list)"

emit "app_a_system=$(printf '%s\n' "$system_a" | paste -sd ',' -)"
emit "app_aaaa=$(printf '%s\n' "$system_aaaa" | paste -sd ',' -)"
emit "app_cname=$(printf '%s\n' "$cname" | paste -sd ',' -)"
emit "resolver_1_1_1_1=$(printf '%s\n' "$resolver_1111" | paste -sd ',' -)"
emit "resolver_8_8_8_8=$(printf '%s\n' "$resolver_8888" | paste -sd ',' -)"

if [[ -n "$system_aaaa" ]]; then
  STATE="UNEXPECTED_IPV6"
  emit "state=$STATE"
  finish 1
fi

if [[ -z "$system_a" && -z "$resolver_1111" && -z "$resolver_8888" ]]; then
  STATE="APP_A_RECORD_MISSING"
  emit "state=$STATE"
  finish 1
fi

if [[ "$(join_by_comma $system_a)" != "$EXPECTED_IPV4" || "$(join_by_comma $resolver_1111)" != "$EXPECTED_IPV4" || "$(join_by_comma $resolver_8888)" != "$EXPECTED_IPV4" ]]; then
  STATE="APP_A_RECORD_WRONG"
  if [[ "$system_a" == "$EXPECTED_IPV4" && "$resolver_1111" != "$resolver_8888" ]]; then
    STATE="RESOLVER_DISAGREEMENT"
  fi
  emit "state=$STATE"
  finish 1
fi

emit "dns_trace_tail_begin"
trace_output="$(dig_trace | sed 's/^/trace: /')"
while IFS= read -r line; do
  [[ -n "$line" ]] && emit "$line"
done <<< "$trace_output"
emit "dns_trace_tail_end"

http_status="$(curl_status "http://${APP_DOMAIN}/health/live")"
emit "http_port_80_status=${http_status:-000}"
if [[ "$http_status" == "000" || "$http_status" == "502" || "$http_status" == "503" || "$http_status" == "504" ]]; then
  STATE="DNS_OK_HTTP_UNREACHABLE"
  emit "state=$STATE"
  finish 1
fi

STATE="DNS_OK"
emit "state=$STATE"
finish 0
