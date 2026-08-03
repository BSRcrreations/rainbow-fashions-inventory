#!/usr/bin/env bash
# Archive all application-uploaded files without modifying their source paths.
set -Eeuo pipefail

CONFIG_FILE="${BACKUP_CONFIG_FILE:-/etc/rainbow-fashions/backup.env}"
[[ -r "$CONFIG_FILE" ]] && source "$CONFIG_FILE"

: "${BACKUP_LOCAL_PATH:=/u02/backups}"
: "${BACKUP_RETENTION_DAYS:=30}"
: "${UPLOAD_ARCHIVE_ROOT:=/u02/rainbow/uploads}"
[[ "$BACKUP_RETENTION_DAYS" =~ ^[1-9][0-9]*$ ]] || { echo "BACKUP_RETENTION_DAYS must be a positive integer" >&2; exit 2; }
[[ -d "$UPLOAD_ARCHIVE_ROOT" ]] || { echo "UPLOAD_ARCHIVE_ROOT is not a directory: $UPLOAD_ARCHIVE_ROOT" >&2; exit 2; }

UPLOADS_DIR="$BACKUP_LOCAL_PATH/uploads"
STATUS_DIR="$BACKUP_LOCAL_PATH/status"
LOG_DIR="$BACKUP_LOCAL_PATH/logs"
mkdir -p "$UPLOADS_DIR" "$STATUS_DIR" "$LOG_DIR"
chmod 700 "$UPLOADS_DIR" "$STATUS_DIR" "$LOG_DIR"
umask 077

TIMESTAMP="$(date '+%Y-%m-%d_%H-%M-%S')"
ARCHIVE_NAME="rainbow_inventory_uploads_${TIMESTAMP}.tar.gz"
ARCHIVE_FILE="$UPLOADS_DIR/$ARCHIVE_NAME"
PARTIAL_FILE="${ARCHIVE_FILE}.partial"
FILE_LIST="$(mktemp "$UPLOADS_DIR/.uploads-list.XXXXXX")"
STARTED_AT="$(date --iso-8601=seconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S%z')"
START_EPOCH="$(date +%s)"
RESULT=failed
ARCHIVE_SIZE=0
CHECKSUM=""
FILE_COUNT=0

log() { printf '%s uploads-backup %s\n' "$(date --iso-8601=seconds 2>/dev/null || date)" "$*" | tee -a "$LOG_DIR/uploads-backup.log" >&2; }
json_escape() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }
write_status() {
  local message="$1"
  printf '{"component":"uploads","status":"%s","started_at":"%s","finished_at":"%s","file":"%s","file_size_bytes":%s,"file_count":%s,"sha256":"%s","duration_seconds":%s,"message":"%s"}\n' \
    "$RESULT" "$STARTED_AT" "$(date --iso-8601=seconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S%z')" "$ARCHIVE_NAME" "$ARCHIVE_SIZE" "$FILE_COUNT" "$CHECKSUM" "$(( $(date +%s) - START_EPOCH ))" "$(json_escape "$message")" > "${STATUS_DIR}/latest-uploads-backup.json"
  chmod 600 "${STATUS_DIR}/latest-uploads-backup.json"
}
on_error() {
  local code="$?"
  rm -f "$PARTIAL_FILE"
  write_status "Uploads backup failed (exit ${code})."
  log "result=failed exit_code=${code} file=${ARCHIVE_NAME}"
  exit "$code"
}
trap on_error ERR
trap 'rm -f "$FILE_LIST"' EXIT

ROOT_PATH="$(cd "$UPLOAD_ARCHIVE_ROOT" && pwd -P)"
declare -a requested_paths=()
# APPLICATION_UPLOAD_PATH takes precedence because it captures every current
# and future child directory in one archive.
if [[ -n "${APPLICATION_UPLOAD_PATH:-}" ]]; then
  requested_paths+=("$APPLICATION_UPLOAD_PATH")
else
  for variable_name in PRODUCT_IMAGE_PATH BRAND_IMAGE_PATH INVOICE_UPLOAD_PATH OCR_UPLOAD_PATH SUPPLIER_DOCUMENT_PATH; do
    [[ -n "${!variable_name:-}" ]] && requested_paths+=("${!variable_name}")
  done
  if [[ -n "${ADDITIONAL_UPLOAD_PATHS:-}" ]]; then
    IFS=':' read -r -a additional_paths <<< "$ADDITIONAL_UPLOAD_PATHS"
    requested_paths+=("${additional_paths[@]}")
  fi
fi
[[ "${#requested_paths[@]}" -gt 0 ]] || { log "Set APPLICATION_UPLOAD_PATH or at least one configured upload path"; exit 2; }

declare -a archive_paths=()
for configured_path in "${requested_paths[@]}"; do
  [[ -d "$configured_path" ]] || { log "Configured upload directory is missing: $configured_path"; exit 1; }
  resolved_path="$(cd "$configured_path" && pwd -P)"
  [[ "$resolved_path" == "$ROOT_PATH" || "$resolved_path" == "$ROOT_PATH"/* ]] || { log "Upload directory must be inside UPLOAD_ARCHIVE_ROOT: $configured_path"; exit 2; }
  relative_path="${resolved_path#"$ROOT_PATH"/}"
  [[ "$resolved_path" == "$ROOT_PATH" ]] && relative_path="."
  already_added=false
  for existing_path in "${archive_paths[@]-}"; do
    [[ "$existing_path" == "$relative_path" ]] && already_added=true && break
  done
  if [[ "$already_added" == false ]]; then
    printf '%s\0' "$relative_path" >> "$FILE_LIST"
    archive_paths+=("$relative_path")
  fi
done

command -v tar >/dev/null || { log "tar is not installed"; exit 127; }
log "start=${STARTED_AT} archive=${ARCHIVE_NAME} paths=${archive_paths[*]}"
# GNU tar retains mtimes by default. --null and --verbatim-files-from make
# whitespace and unusual filenames safe; the archive contains root-relative paths.
tar --create --gzip --file="$PARTIAL_FILE" --directory="$ROOT_PATH" --null --verbatim-files-from --files-from="$FILE_LIST"
[[ -s "$PARTIAL_FILE" ]] || { log "tar produced an empty archive"; exit 1; }
tar --list --gzip --file="$PARTIAL_FILE" >/dev/null
FILE_COUNT="$(tar --list --gzip --file="$PARTIAL_FILE" | wc -l | tr -d ' ')"
mv "$PARTIAL_FILE" "$ARCHIVE_FILE"
rm -f "$FILE_LIST"
chmod 600 "$ARCHIVE_FILE"
ARCHIVE_SIZE="$(stat -c '%s' "$ARCHIVE_FILE" 2>/dev/null || stat -f '%z' "$ARCHIVE_FILE")"
if command -v sha256sum >/dev/null; then CHECKSUM="$(sha256sum "$ARCHIVE_FILE" | awk '{print $1}')"; else CHECKSUM="$(shasum -a 256 "$ARCHIVE_FILE" | awk '{print $1}')"; fi
printf '%s  %s\n' "$CHECKSUM" "$ARCHIVE_NAME" > "${ARCHIVE_FILE}.sha256"
chmod 600 "${ARCHIVE_FILE}.sha256"
find "$UPLOADS_DIR" -xdev -type f \( -name 'rainbow_inventory_uploads_*.tar.gz' -o -name 'rainbow_inventory_uploads_*.tar.gz.sha256' \) -mtime "+$BACKUP_RETENTION_DAYS" -delete
RESULT=success
write_status "Uploads archive verified and retained for ${BACKUP_RETENTION_DAYS} days."
log "result=success file=${ARCHIVE_NAME} size_bytes=${ARCHIVE_SIZE} file_count=${FILE_COUNT} sha256=${CHECKSUM}"
