#!/usr/bin/env bash
# Check backup filesystem capacity and publish a status. Optional webhook alerts
# are intentionally limited to a short, credential-free payload.
set -Eeuo pipefail
CONFIG_FILE="${BACKUP_CONFIG_FILE:-/etc/rainbow-fashions/backup.env}"
[[ -r "$CONFIG_FILE" ]] && source "$CONFIG_FILE"
: "${BACKUP_LOCAL_PATH:=/u02/backups}"
: "${BACKUP_DISK_WARNING_PERCENT:=80}"
: "${BACKUP_DISK_CRITICAL_PERCENT:=90}"
[[ "$BACKUP_DISK_WARNING_PERCENT" =~ ^[0-9]{1,3}$ && "$BACKUP_DISK_CRITICAL_PERCENT" =~ ^[0-9]{1,3}$ && "$BACKUP_DISK_WARNING_PERCENT" -lt "$BACKUP_DISK_CRITICAL_PERCENT" && "$BACKUP_DISK_CRITICAL_PERCENT" -le 100 ]] || { echo "Invalid backup disk thresholds" >&2; exit 2; }
mkdir -p "$BACKUP_LOCAL_PATH/status"; chmod 700 "$BACKUP_LOCAL_PATH/status"
read -r _ blocks used available capacity _ < <(df -Pk "$BACKUP_LOCAL_PATH" | awk 'NR==2 {print $1, $2, $3, $4, $5, $6}')
percent="${capacity%%%}"; status=success; message="Backup filesystem usage is ${percent}%."
if (( percent >= BACKUP_DISK_CRITICAL_PERCENT )); then status=critical; message="CRITICAL: ${message}"; elif (( percent >= BACKUP_DISK_WARNING_PERCENT )); then status=warning; message="WARNING: ${message}"; fi
printf '{"component":"disk","status":"%s","checked_at":"%s","usage_percent":%s,"available_kb":%s,"message":"%s"}\n' "$status" "$(date --iso-8601=seconds 2>/dev/null || date)" "$percent" "$available" "$message" > "$BACKUP_LOCAL_PATH/status/latest-disk-status.json"
chmod 600 "$BACKUP_LOCAL_PATH/status/latest-disk-status.json"
if [[ "$status" != success && -n "${BACKUP_ALERT_WEBHOOK_URL:-}" ]]; then
  command -v curl >/dev/null || { echo "$message (curl unavailable for alert)" >&2; exit 1; }
  curl --fail --silent --show-error --max-time 15 -H 'Content-Type: application/json' --data "{\"service\":\"rainbow-fashions-backup\",\"severity\":\"${status}\",\"message\":\"${message}\"}" "$BACKUP_ALERT_WEBHOOK_URL"
fi
[[ "$status" != critical ]]
