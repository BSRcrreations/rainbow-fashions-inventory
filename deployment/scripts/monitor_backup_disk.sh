#!/usr/bin/env bash
# Monitor every storage location and backup freshness; alerts never contain secrets.
set -Eeuo pipefail
CONFIG_FILE="${BACKUP_CONFIG_FILE:-/etc/rainbow-fashions/backup.env}"
[[ -r "$CONFIG_FILE" ]] && source "$CONFIG_FILE"
: "${BACKUP_LOCAL_PATH:=/u02/backups}"
: "${DISK_WARNING_PERCENT:=75}"
: "${DISK_CRITICAL_PERCENT:=85}"
: "${DISK_EMERGENCY_PERCENT:=95}"
: "${DISK_MIN_FREE_GB:=10}"
: "${BACKUP_MAX_AGE_HOURS:=26}"
: "${BACKUP_MONITOR_PATHS:=$BACKUP_LOCAL_PATH:${APPLICATION_UPLOAD_PATH:-}}"
[[ "$DISK_WARNING_PERCENT" -lt "$DISK_CRITICAL_PERCENT" && "$DISK_CRITICAL_PERCENT" -lt "$DISK_EMERGENCY_PERCENT" && "$DISK_EMERGENCY_PERCENT" -le 100 ]] || { echo "Invalid disk thresholds" >&2; exit 2; }

STATUS_DIR="$BACKUP_LOCAL_PATH/status"; LOG_DIR="$BACKUP_LOCAL_PATH/logs"; mkdir -p "$STATUS_DIR" "$LOG_DIR"; chmod 700 "$STATUS_DIR" "$LOG_DIR"
LOG_FILE="$LOG_DIR/disk-monitor.log"; touch "$LOG_FILE"; chmod 600 "$LOG_FILE"
log() { printf '%s disk-monitor %s\n' "$(date --iso-8601=seconds 2>/dev/null || date)" "$*" | tee -a "$LOG_FILE" >&2; }
declare -a alerts=(); highest=success; maximum_usage=0; minimum_free_kb=0
rank() { case "$1" in success) echo 0;; warning) echo 1;; critical) echo 2;; emergency) echo 3;; failed) echo 4;; esac; }
set_status() { [[ "$(rank "$1")" -gt "$(rank "$highest")" ]] && highest="$1"; }

IFS=':' read -r -a monitor_paths <<< "$BACKUP_MONITOR_PATHS"
for path in "${monitor_paths[@]}"; do
  [[ -n "$path" && -e "$path" ]] || continue
  read -r _ _ _ available capacity _ < <(df -Pk "$path" | awk 'NR==2 {print $1, $2, $3, $4, $5, $6}')
  used_percent="${capacity%%%}"
  (( used_percent > maximum_usage )) && maximum_usage="$used_percent"
  [[ "$minimum_free_kb" -eq 0 || "$available" -lt "$minimum_free_kb" ]] && minimum_free_kb="$available"
  level=success
  if (( used_percent >= DISK_EMERGENCY_PERCENT )); then level=emergency; elif (( used_percent >= DISK_CRITICAL_PERCENT )); then level=critical; elif (( used_percent >= DISK_WARNING_PERCENT )); then level=warning; fi
  if (( available < DISK_MIN_FREE_GB * 1024 * 1024 )); then level=critical; alerts+=("free space below ${DISK_MIN_FREE_GB}GB on ${path}"); fi
  [[ "$level" == success ]] || alerts+=("${path} is ${used_percent}% used (${level})")
  set_status "$level"
done

for backup_dir in "$BACKUP_LOCAL_PATH/database" "$BACKUP_LOCAL_PATH/uploads"; do
  latest="$(find "$backup_dir" -maxdepth 1 -type f \( -name '*.dump' -o -name '*.tar.gz' \) -print 2>/dev/null | sort | tail -n 1)"
  if [[ -z "$latest" ]]; then alerts+=("missing backup in ${backup_dir}"); set_status failed; continue; fi
  age_seconds="$(( $(date +%s) - $(stat -c '%Y' "$latest" 2>/dev/null || stat -f '%m' "$latest") ))"
  if (( age_seconds > BACKUP_MAX_AGE_HOURS * 3600 )); then alerts+=("backup older than ${BACKUP_MAX_AGE_HOURS} hours: $(basename "$latest")"); set_status failed; fi
  mapfile -t recent < <(find "$backup_dir" -maxdepth 1 -type f \( -name '*.dump' -o -name '*.tar.gz' \) -print 2>/dev/null | sort | tail -n 2)
  if (( ${#recent[@]} == 2 )); then
    latest_size="$(stat -c '%s' "${recent[1]}" 2>/dev/null || stat -f '%z' "${recent[1]}")"; previous_size="$(stat -c '%s' "${recent[0]}" 2>/dev/null || stat -f '%z' "${recent[0]}")"
    if (( latest_size * 100 < previous_size * 50 )); then alerts+=("backup size dropped by more than 50%: $(basename "${recent[1]}")"); set_status warning; fi
  fi
done

if [[ -s "$STATUS_DIR/latest-offsite-backup.json" ]] && ! grep -q '"status":"success"' "$STATUS_DIR/latest-offsite-backup.json"; then alerts+=("latest remote upload failed"); set_status failed; fi
if [[ -s "$STATUS_DIR/latest-restore-test.json" ]] && ! grep -q '"status":"success"' "$STATUS_DIR/latest-restore-test.json"; then alerts+=("latest restore test failed"); set_status failed; fi
message="Backup monitoring healthy."; (( ${#alerts[@]} )) && message="$(IFS='; '; echo "${alerts[*]}")"
printf '{"component":"disk","status":"%s","checked_at":"%s","usage_percent":%s,"available_kb":%s,"message":"%s"}\n' "$highest" "$(date --iso-8601=seconds 2>/dev/null || date)" "$maximum_usage" "$minimum_free_kb" "${message//\"/\\\"}" > "$STATUS_DIR/latest-disk-status.json"
chmod 600 "$STATUS_DIR/latest-disk-status.json"
log "status=${highest} ${message}"
if [[ "$highest" != success ]]; then
  payload="{\"service\":\"rainbow-fashions-backup\",\"severity\":\"${highest}\",\"message\":\"${message//\"/\\\"}\"}"
  for webhook in "${BACKUP_ALERT_WEBHOOK_URL:-}" "${BACKUP_SLACK_WEBHOOK:-}" "${BACKUP_TEAMS_WEBHOOK:-}"; do
    [[ -n "$webhook" ]] && curl --fail --silent --show-error --max-time 15 -H 'Content-Type: application/json' --data "$payload" "$webhook" || true
  done
  if [[ -n "${BACKUP_ALERT_EMAIL:-}" ]] && command -v mail >/dev/null; then printf '%s\n' "$message" | mail -s "Rainbow backup ${highest}" "$BACKUP_ALERT_EMAIL" || true; fi
fi
[[ "$highest" == success || "$highest" == warning ]]
