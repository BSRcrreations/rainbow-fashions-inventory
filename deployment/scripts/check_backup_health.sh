#!/usr/bin/env bash
# Check recovery evidence, capacity, and service failures. A remote alert is
# sent only for a changed unhealthy state or a recovery notification.
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib_backup.sh"

ALERT_ENV="${RAINBOW_ALERTS_ENV:-${RAINBOW_SHARED_DIR}/backup-alerts.env}"
[[ -r "$ALERT_ENV" ]] && source "$ALERT_ENV"
DATABASE_BACKUP_MAX_AGE_HOURS="${DATABASE_BACKUP_MAX_AGE_HOURS:-30}"
OFFSITE_BACKUP_MAX_AGE_HOURS="${OFFSITE_BACKUP_MAX_AGE_HOURS:-36}"
RESTORE_TEST_MAX_AGE_DAYS="${RESTORE_TEST_MAX_AGE_DAYS:-8}"
DISK_WARNING_PERCENT="${DISK_WARNING_PERCENT:-75}"
DISK_CRITICAL_PERCENT="${DISK_CRITICAL_PERCENT:-85}"
INODE_WARNING_PERCENT="${INODE_WARNING_PERCENT:-80}"
ALERT_SUPPRESSION_MINUTES="${ALERT_SUPPRESSION_MINUTES:-60}"
test_mode=false
[[ "${1:-}" == "--test-alert" ]] && test_mode=true
[[ -z "${1:-}" || "${1:-}" == "--test-alert" ]] || backup_die "Usage: $0 [--test-alert]"

backup_require_command python3
backup_init_log backup-health.log
backup_lock backup-health

status_value() {
  local file="$1" key="$2"
  python3 - "$file" "$key" <<'PY'
import json
import sys
try:
    print(json.load(open(sys.argv[1], encoding='utf-8')).get(sys.argv[2], ''))
except (FileNotFoundError, json.JSONDecodeError):
    print('')
PY
}
age_hours() {
  python3 - "$1" <<'PY'
from datetime import datetime, timezone
import sys
value = sys.argv[1].replace('Z', '+00:00')
try:
    then = datetime.fromisoformat(value)
    print(int((datetime.now(timezone.utc) - then.astimezone(timezone.utc)).total_seconds() // 3600))
except ValueError:
    print(999999)
PY
}
age_minutes() {
  python3 - "$1" <<'PY'
from datetime import datetime, timezone
import sys
value = sys.argv[1].replace('Z', '+00:00')
try:
    then = datetime.fromisoformat(value)
    print(int((datetime.now(timezone.utc) - then.astimezone(timezone.utc)).total_seconds() // 60))
except ValueError:
    print(999999)
PY
}

declare -a failures=()
check_evidence() {
  local name="$1" file="$2" maximum="$3" unit="$4"
  local status timestamp age
  status="$(status_value "$file" status)"
  timestamp="$(status_value "$file" timestamp)"
  [[ "$status" == SUCCESS ]] || failures+=("${name}: no successful evidence")
  age="$(age_hours "$timestamp")"
  if [[ "$unit" == days ]]; then maximum=$((maximum * 24)); fi
  (( age <= maximum )) || failures+=("${name}: evidence age ${age}h exceeds ${maximum}h")
}

check_evidence database "${RAINBOW_BACKUP_STATUS_DIR}/latest-database-backup.json" "$DATABASE_BACKUP_MAX_AGE_HOURS" hours
check_evidence offsite "${RAINBOW_BACKUP_STATUS_DIR}/latest-offsite-backup.json" "$OFFSITE_BACKUP_MAX_AGE_HOURS" hours
check_evidence database_restore "${RAINBOW_BACKUP_STATUS_DIR}/latest-database-restore-test.json" "$RESTORE_TEST_MAX_AGE_DAYS" days
check_evidence uploads "${RAINBOW_BACKUP_STATUS_DIR}/latest-upload-manifest.json" "$DATABASE_BACKUP_MAX_AGE_HOURS" hours
check_evidence upload_restore "${RAINBOW_BACKUP_STATUS_DIR}/latest-upload-restore-test.json" "$RESTORE_TEST_MAX_AGE_DAYS" days

for service in rainbow-database-backup.service rainbow-offsite-backup.service rainbow-backup-retention.service; do
  if command -v systemctl >/dev/null 2>&1 && systemctl is-failed --quiet "$service"; then
    failures+=("${service}: failed")
  fi
done

read -r root_percent backup_percent inode_percent < <(python3 - "$RAINBOW_BACKUP_ROOT" <<'PY'
import os
import shutil
import sys
root = shutil.disk_usage('/')
backup = shutil.disk_usage(sys.argv[1])
stat = os.statvfs('/')
inode = 100 * (stat.f_files - stat.f_ffree) // stat.f_files if stat.f_files else 0
print(100 * root.used // root.total, 100 * backup.used // backup.total, inode)
PY
)
(( root_percent < DISK_CRITICAL_PERCENT )) || failures+=("root disk: ${root_percent}% is critical")
(( backup_percent < DISK_CRITICAL_PERCENT )) || failures+=("backup disk: ${backup_percent}% is critical")
(( inode_percent < INODE_WARNING_PERCENT )) || failures+=("root inodes: ${inode_percent}% exceeds warning")

state_file="${RAINBOW_BACKUP_STATUS_DIR}/backup-health-state.json"
current_state=HEALTHY
[[ "${#failures[@]}" -eq 0 ]] || current_state=UNHEALTHY
previous_state="$(status_value "$state_file" state)"
previous_timestamp="$(status_value "$state_file" timestamp)"
previous_age_minutes="$(age_minutes "$previous_timestamp")"
message="Backup health is healthy."
[[ "$current_state" == UNHEALTHY ]] && message="$(IFS='; '; echo "${failures[*]}")"

send_alert() {
  local severity="$1" body="$2"
  [[ -n "${BACKUP_ALERT_WEBHOOK_URL:-}" ]] || return 3
  backup_require_command curl
  python3 - "$severity" "$body" <<'PY' | curl --fail --silent --show-error --max-time 15 -H 'Content-Type: application/json' --data-binary @- "$BACKUP_ALERT_WEBHOOK_URL"
import json
import socket
import sys
print(json.dumps({'service': 'rainbow-fashions-backup', 'severity': sys.argv[1],
                  'hostname': socket.gethostname(), 'timestamp': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
                  'message': sys.argv[2]}))
PY
}

docker_disk_summary=UNAVAILABLE
if command -v docker >/dev/null 2>&1; then
  docker_disk_summary="$(docker system df --format 'Images={{.Size}} Containers={{.Size}} Volumes={{.Size}}' 2>/dev/null | tr '\n' ';' || true)"
fi

alert_result=NOT_CONFIGURED
if [[ "$test_mode" == true ]]; then
  if send_alert TEST_WARNING "Backup alert delivery test: warning" && send_alert TEST_CRITICAL "Backup alert delivery test: critical" && send_alert TEST_RECOVERY "Backup alert delivery test: recovery"; then
    alert_result=SENT
  else
    alert_result=FAILED
  fi
  backup_write_json "${RAINBOW_BACKUP_STATUS_DIR}/latest-alert-test.json" \
    "timestamp=$(backup_now)" "alert_channel=${BACKUP_ALERT_WEBHOOK_URL:+WEBHOOK}" \
    "warning_delivery=${alert_result}" "critical_delivery=${alert_result}" \
    "recovery_delivery=${alert_result}" "duplicate_suppression=CONFIGURED" "result=${alert_result}"
elif [[ "$current_state" != "$previous_state" || ( "$current_state" == UNHEALTHY && "$previous_age_minutes" -ge "$ALERT_SUPPRESSION_MINUTES" ) ]]; then
  severity=RECOVERY
  [[ "$current_state" == UNHEALTHY ]] && severity=CRITICAL
  if send_alert "$severity" "$message"; then alert_result=SENT; else alert_result=NOT_CONFIGURED; fi
fi

backup_write_json "$state_file" "timestamp=$(backup_now)" "state=${current_state}" \
  "message=${message}" "root_disk_percent=${root_percent}" "backup_disk_percent=${backup_percent}" \
  "inode_percent=${inode_percent}" "docker_disk=${docker_disk_summary}" "alert_result=${alert_result}"
backup_log "backup_health state=${current_state} alert=${alert_result} message=${message}"
[[ "$current_state" == HEALTHY ]] || exit 1
[[ "$test_mode" == false || "$alert_result" == SENT ]] || exit 3
