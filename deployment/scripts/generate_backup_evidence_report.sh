#!/usr/bin/env bash
# Combine status metadata into a redacted, reviewable recovery evidence report.
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib_backup.sh"

backup_require_command python3
backup_init_log backup-evidence.log
backup_lock backup-evidence

timestamp="$(backup_timestamp)"
evidence_dir="${RAINBOW_BACKUP_ROOT}/evidence"
json_report="${evidence_dir}/backup_evidence_${timestamp}.json"
text_report="${evidence_dir}/backup_evidence_${timestamp}.txt"
mkdir -p "$evidence_dir"
chmod 700 "$evidence_dir"

timer_state=unknown
if command -v systemctl >/dev/null 2>&1; then
  if systemctl is-enabled --quiet rainbow-database-backup.timer && systemctl is-active --quiet rainbow-database-backup.timer; then
    timer_state=enabled-active
  else
    timer_state=not-ready
  fi
fi

python3 - "$json_report" "$text_report" "$RAINBOW_BACKUP_ROOT" "$RAINBOW_BACKUP_STATUS_DIR" "$(backup_deployed_commit)" "$timer_state" <<'PY'
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

json_path, text_path, root, status_root, commit = map(Path, sys.argv[1:6])
timer_state = sys.argv[6]
def read(name):
    try:
        return json.loads((status_root / name).read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError):
        return {'status': 'MISSING'}

database = read('latest-database-backup.json')
uploads = read('latest-upload-manifest.json')
offsite = read('latest-offsite-backup.json')
restore = read('latest-database-restore-test.json')
upload_restore = read('latest-upload-restore-test.json')
retention = read('latest-retention-report.json')
alert = read('latest-alert-test.json')
required = {'database': database, 'uploads': uploads, 'offsite': offsite,
            'database_restore': restore, 'upload_restore': upload_restore,
            'retention': retention, 'alert_test': alert}
failed = [name for name, value in required.items() if value.get('status', value.get('result')) not in ('SUCCESS', 'SENT')]
if timer_state != 'enabled-active':
    failed.append('daily_database_timer')
report = {'timestamp': datetime.now(timezone.utc).isoformat(), 'deployed_git_commit': str(commit),
          'database': database, 'uploads': uploads, 'offsite': offsite,
          'database_restore': restore, 'upload_restore': upload_restore,
          'retention': retention, 'alert_test': alert,
          'daily_database_timer': timer_state,
          'root_disk_percent': 100 * shutil.disk_usage('/').used // shutil.disk_usage('/').total,
          'backup_storage_bytes': sum(path.stat().st_size for path in Path(root).rglob('*') if path.is_file()),
          'overall_status': 'PROTECTED' if not failed else 'AT_RISK',
          'failed_requirements': failed}
json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
os.chmod(json_path, 0o600)
text_path.write_text('\n'.join([f'Rainbow Fashions backup evidence: {report["overall_status"]}',
                                 f'Deployed commit: {report["deployed_git_commit"]}',
                                 f'Failed requirements: {", ".join(failed) if failed else "none"}']) + '\n', encoding='utf-8')
os.chmod(text_path, 0o600)
PY
backup_log "backup_evidence_generated report=${json_report}"
printf '%s\n' "$json_report"
