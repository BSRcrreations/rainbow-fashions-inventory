#!/usr/bin/env bash
# Archive the host bind-mounted application uploads and record a checksum
# manifest. Source files are only read; this does not stop the application.
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=deployment/scripts/lib_backup.sh
source "${SCRIPT_DIR}/lib_backup.sh"

backup_require_command docker
backup_require_command python3
backup_require_command tar
backup_init_log uploads-backup.log
backup_lock uploads-backup
backup_load_backend_env

source_dir="$(backup_upload_source)"
timestamp="$(backup_timestamp)"
date_path="$(date -u '+%Y/%m/%d')"
uploads_dir="${RAINBOW_BACKUP_ROOT}/uploads/${date_path}"
archive_name="rainbow_uploads_${timestamp}.tar.gz"
archive_file="${uploads_dir}/${archive_name}"
partial_file="${archive_file}.partial"
manifest_file="${uploads_dir}/${archive_name}.manifest.json"
checksum_file="${archive_file}.sha256"
status_file="${RAINBOW_BACKUP_STATUS_DIR}/latest-upload-manifest.json"
file_list="$(mktemp "${TMPDIR:-/tmp}/rainbow-upload-files.XXXXXX")"
started_epoch="$(date +%s)"

mkdir -p "$uploads_dir"
chmod 700 "$uploads_dir"
umask 077
cleanup() { rm -f "$file_list" "$partial_file"; }
trap cleanup EXIT

# Cache, partial transfers, and disposable thumbnails are excluded; originals
# under products/ and brands/ remain in the archive and manifest.
(cd "$source_dir" && find . -type f \
  ! -path './cache/*' ! -path '*/cache/*' \
  ! -path './thumbnails/*' ! -path '*/thumbnails/*' \
  ! -name '*.partial' ! -name '*.tmp' -print0) > "$file_list"
file_count="$(tr -cd '\0' < "$file_list" | wc -c | tr -d ' ')"

tar --create --gzip --file="$partial_file" --directory="$source_dir" \
  --null --verbatim-files-from --files-from="$file_list"
[[ -s "$partial_file" ]] || backup_die "The uploads archive is empty."
tar --list --gzip --file="$partial_file" >/dev/null
mv "$partial_file" "$archive_file"
chmod 600 "$archive_file"
checksum="$(backup_sha256 "$archive_file")"
printf '%s  %s\n' "$checksum" "$archive_name" > "$checksum_file"
backup_check_sha256 "$archive_file" || backup_die "Uploads archive checksum validation failed."

python3 - "$source_dir" "$file_list" "$manifest_file" <<'PY'
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(sys.argv[1]).resolve()
files = []
product_count = brand_count = total_bytes = 0
for raw in Path(sys.argv[2]).read_bytes().split(b'\0'):
    if not raw:
        continue
    relative = raw.decode('utf-8', 'surrogateescape').lstrip('./')
    path = root / relative
    stat = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    product_count += int(relative.startswith('products/'))
    brand_count += int(relative.startswith('brands/'))
    total_bytes += stat.st_size
    files.append({'relative_path': relative, 'size_bytes': stat.st_size,
                  'modified_at': datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                  'sha256': digest.hexdigest()})
payload = {'timestamp': datetime.now(timezone.utc).isoformat(), 'source_root': str(root),
           'product_image_count': product_count, 'brand_logo_count': brand_count,
           'total_file_count': len(files), 'total_bytes': total_bytes, 'files': files}
destination = Path(sys.argv[3])
temporary = destination.with_suffix(destination.suffix + '.partial')
temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
os.chmod(temporary, 0o600)
temporary.replace(destination)
PY

size="$(backup_file_size "$archive_file")"
duration="$(( $(date +%s) - started_epoch ))"
product_count="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["product_image_count"])' "$manifest_file")"
brand_count="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["brand_logo_count"])' "$manifest_file")"
postgres_container="$(backup_postgres_container)"
# Brand logos currently share the products upload directory. Count their
# catalogue references separately so zero brand-directory files is not mistaken
# for missing protected logos.
catalogue_product_images="$(docker exec -i "$postgres_container" sh -ceu 'export PGPASSWORD="$POSTGRES_PASSWORD"; psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SELECT count(*) FROM products WHERE image_url IS NOT NULL"')"
catalogue_brand_logos="$(docker exec -i "$postgres_container" sh -ceu 'export PGPASSWORD="$POSTGRES_PASSWORD"; psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SELECT count(*) FROM brands WHERE logo_url IS NOT NULL"')"
backup_write_json "$status_file" \
  "timestamp=$(backup_now)" "status=SUCCESS" "archive_path=${archive_file}" \
  "archive_filename=${archive_name}" "archive_size_bytes=${size}" "sha256=${checksum}" \
  "manifest_path=${manifest_file}" "product_directory_file_count=${product_count}" \
  "brand_directory_file_count=${brand_count}" "product_image_count=${catalogue_product_images}" \
  "brand_logo_count=${catalogue_brand_logos}" "total_file_count=${file_count}" "duration_seconds=${duration}"
backup_log "uploads_backup_succeeded archive=${archive_name} files=${file_count} product_images=${catalogue_product_images} brand_logos=${catalogue_brand_logos}"
