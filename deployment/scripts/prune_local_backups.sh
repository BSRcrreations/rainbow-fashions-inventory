#!/usr/bin/env bash
# Retention is intentionally dry-run by default. A review must precede --execute.
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib_backup.sh"

mode=dry-run
[[ "${1:-}" == "--execute" ]] && mode=execute
[[ -z "${1:-}" || "${1:-}" == "--execute" ]] || backup_die "Usage: $0 [--execute]"
backup_require_command python3
backup_init_log backup-retention.log
backup_lock retention

database_root="${RAINBOW_BACKUP_ROOT}/database"
[[ -d "$database_root" ]] || backup_die "Database backup root is missing: $database_root"
[[ "$(python3 - "$database_root" <<'PY'
import os,sys
print(os.path.realpath(sys.argv[1]))
PY
)" == "$(python3 - "$RAINBOW_BACKUP_ROOT/database" <<'PY'
import os,sys
print(os.path.realpath(sys.argv[1]))
PY
)" ]] || backup_die "Resolved database backup path is unexpected."

# Avoid racing an offsite upload or restore test. The latest valid set is always retained.
for lock in offsite-backup restore-test; do
  if [[ -e "${RAINBOW_BACKUP_ROOT}/.locks/${lock}.lock" ]] && ! flock -n "${RAINBOW_BACKUP_ROOT}/.locks/${lock}.lock" true; then
    backup_die "Refusing retention while ${lock} is active."
  fi
done

report="${RAINBOW_BACKUP_STATUS_DIR}/latest-retention-report.json"
result="$(python3 - "$database_root" "$mode" <<'PY'
import datetime as dt
import json
import os
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
mode = sys.argv[2]
sets = []
for dump in root.rglob('rainbow_inventory_*.dump'):
    checksum = dump.with_suffix(dump.suffix + '.sha256')
    metadata = dump.with_suffix(dump.suffix + '.metadata.json')
    if not checksum.is_file() or not metadata.is_file() or dump.stat().st_size == 0:
        continue
    timestamp = dt.datetime.strptime(dump.stem.removeprefix('rainbow_inventory_'), '%Y%m%d_%H%M%S').replace(tzinfo=dt.timezone.utc)
    sets.append((timestamp, dump, checksum, metadata))
sets.sort(reverse=True)
keep = set()
now = dt.datetime.now(dt.timezone.utc)
daily = set()
weekly = set()
monthly = set()
for timestamp, dump, checksum, metadata in sets:
    day_key = timestamp.date()
    week_key = (timestamp.isocalendar().year, timestamp.isocalendar().week)
    month_key = (timestamp.year, timestamp.month)
    month_age = (now.year - timestamp.year) * 12 + now.month - timestamp.month
    if (now.date() - day_key).days < 14 and day_key not in daily:
        keep.add(dump)
        daily.add(day_key)
    if (now - timestamp).days < 56 and week_key not in weekly:
        keep.add(dump)
        weekly.add(week_key)
    if 0 <= month_age < 12 and month_key not in monthly:
        keep.add(dump)
        monthly.add(month_key)
if sets:
    keep.add(sets[0][1])
remove = [entry for entry in sets if entry[1] not in keep]
bytes_reclaimed = sum(sum(file.stat().st_size for file in files) for _, *files in remove)
if mode == 'execute':
    for _, *files in remove:
        for file in files:
            file.unlink(missing_ok=True)
print(json.dumps({'sets_total': len(sets), 'sets_retained': len(keep), 'sets_removed': len(remove), 'bytes_reclaimed': bytes_reclaimed}))
PY
)"
backup_write_json "$report" "timestamp=$(backup_now)" "result=SUCCESS" "mode=${mode}" \
  "local_policy=daily=14,weekly=8,monthly=12" "summary=${result}"
backup_log "local_retention_completed mode=${mode} ${result}"
