#!/usr/bin/env bash
# Verify a sample from the newest uploads archive in a temporary directory.
# Production uploads are never a restore destination.
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib_backup.sh"

backup_require_command tar
backup_require_command python3
backup_init_log upload-restore-test.log
backup_lock upload-restore-test

archive="$(find "${RAINBOW_BACKUP_ROOT}/uploads" -type f -name 'rainbow_uploads_*.tar.gz' -print 2>/dev/null | sort | tail -n 1)"
[[ -n "$archive" && -s "$archive" ]] || backup_die "No uploads archive is available for restore testing."
backup_check_sha256 "$archive" || backup_die "The selected uploads archive checksum is invalid."
manifest="${archive}.manifest.json"
[[ -s "$manifest" ]] || backup_die "The selected uploads archive has no manifest."

timestamp="$(backup_timestamp)"
target="${TMPDIR:-/tmp}/rainbow-upload-restore-test-${timestamp}"
report_dir="${RAINBOW_BACKUP_ROOT}/restore-tests/$(date -u '+%Y/%m')"
report="${report_dir}/upload_restore_test_${timestamp}.json"
started_epoch="$(date +%s)"
mkdir -p "$target" "$report_dir"
chmod 700 "$target" "$report_dir"
trap 'rm -rf "$target"' EXIT

selection="$(python3 - "$manifest" <<'PY'
import json
import sys

files = json.load(open(sys.argv[1], encoding='utf-8')).get('files', [])
sample = []
for prefix in ('products/', 'brands/'):
    match = next((entry for entry in files if entry['relative_path'].startswith(prefix)), None)
    if match:
        sample.append(match)
print(json.dumps(sample))
PY
)"
sample_count="$(python3 -c 'import json,sys; print(len(json.loads(sys.argv[1])))' "$selection")"
[[ "$sample_count" -gt 0 ]] || backup_die "No product-image or brand-logo sample exists in this archive."

tar --extract --gzip --file="$archive" --directory="$target"
verification="$(python3 - "$target" "$selection" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

target = Path(sys.argv[1])
items = json.loads(sys.argv[2])
for item in items:
    path = target / item['relative_path']
    if not path.is_file() or path.stat().st_size == 0:
        raise SystemExit(f'Missing or empty restored file: {item["relative_path"]}')
    if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
        raise SystemExit(f'Checksum mismatch: {item["relative_path"]}')
print(','.join(item['relative_path'] for item in items))
PY
)"
duration="$(( $(date +%s) - started_epoch ))"
backup_write_json "$report" "snapshot_id=LOCAL_ARCHIVE" "files_restored=${sample_count}" \
  "sample_paths=${verification}" "checksum_result=SUCCESS" "duration_seconds=${duration}" \
  "cleanup_status=SUCCESS" "result=SUCCESS"
backup_write_json "${RAINBOW_BACKUP_STATUS_DIR}/latest-upload-restore-test.json" \
  "timestamp=$(backup_now)" "status=SUCCESS" "report_path=${report}" \
  "files_restored=${sample_count}" "duration_seconds=${duration}"
backup_log "upload_restore_test_succeeded archive=$(basename "$archive") files=${sample_count} duration_seconds=${duration}"
