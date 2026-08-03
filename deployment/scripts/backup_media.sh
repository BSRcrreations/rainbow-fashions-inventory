#!/usr/bin/env bash
# Archive all uploaded media (products, brands, invoices, and future uploads).
set -Eeuo pipefail

CONFIG_FILE="${BACKUP_CONFIG_FILE:-/etc/rainbow-fashions/backup.env}"
[[ -r "$CONFIG_FILE" ]] && source "$CONFIG_FILE"
: "${BACKUP_LOCAL_PATH:=/u02/backups}"
: "${BACKUP_MEDIA_SOURCE:?BACKUP_MEDIA_SOURCE is required and must be the host-mounted uploads directory}"
: "${BACKUP_RETENTION_DAYS:=30}"
[[ -d "$BACKUP_MEDIA_SOURCE" ]] || { echo "BACKUP_MEDIA_SOURCE is not a directory: $BACKUP_MEDIA_SOURCE" >&2; exit 2; }
[[ "$BACKUP_RETENTION_DAYS" =~ ^[1-9][0-9]*$ ]] || { echo "BACKUP_RETENTION_DAYS must be a positive integer" >&2; exit 2; }

MEDIA_DIR="$BACKUP_LOCAL_PATH/media"; STATUS_DIR="$BACKUP_LOCAL_PATH/status"; LOG_DIR="$BACKUP_LOCAL_PATH/logs"
mkdir -p "$MEDIA_DIR" "$STATUS_DIR" "$LOG_DIR"; chmod 700 "$MEDIA_DIR" "$STATUS_DIR" "$LOG_DIR"; umask 077
TIMESTAMP="$(date '+%Y-%m-%d_%H-%M-%S')"; NAME="rainbow_inventory_media_${TIMESTAMP}.tar.gz"; TARGET="$MEDIA_DIR/$NAME"; PARTIAL="${TARGET}.partial"
START="$(date --iso-8601=seconds 2>/dev/null || date)"; START_EPOCH="$(date +%s)"; RESULT=failed; SIZE=0; CHECKSUM=""
log() { printf '%s media-backup %s\n' "$(date --iso-8601=seconds 2>/dev/null || date)" "$*" | tee -a "$LOG_DIR/media-backup.log" >&2; }
write_status() { local msg="$1"; printf '{"component":"media","status":"%s","started_at":"%s","finished_at":"%s","file":"%s","file_size_bytes":%s,"sha256":"%s","duration_seconds":%s,"message":"%s"}\n' "$RESULT" "$START" "$(date --iso-8601=seconds 2>/dev/null || date)" "$NAME" "$SIZE" "$CHECKSUM" "$(( $(date +%s) - START_EPOCH ))" "${msg//\"/\\\"}" > "$STATUS_DIR/latest-media-backup.json"; chmod 600 "$STATUS_DIR/latest-media-backup.json"; }
trap 'code=$?; rm -f "$PARTIAL"; write_status "Media backup failed (exit ${code})."; exit "$code"' ERR

tar --create --gzip --file="$PARTIAL" --directory="$(dirname "$BACKUP_MEDIA_SOURCE")" "$(basename "$BACKUP_MEDIA_SOURCE")"
[[ -s "$PARTIAL" ]] || { log "Archive is empty"; exit 1; }
tar --list --gzip --file="$PARTIAL" >/dev/null
mv "$PARTIAL" "$TARGET"; chmod 600 "$TARGET"
SIZE="$(stat -c '%s' "$TARGET" 2>/dev/null || stat -f '%z' "$TARGET")"
if command -v sha256sum >/dev/null; then CHECKSUM="$(sha256sum "$TARGET" | awk '{print $1}')"; else CHECKSUM="$(shasum -a 256 "$TARGET" | awk '{print $1}')"; fi
printf '%s  %s\n' "$CHECKSUM" "$NAME" > "${TARGET}.sha256"; chmod 600 "${TARGET}.sha256"
find "$MEDIA_DIR" -xdev -type f \( -name 'rainbow_inventory_media_*.tar.gz' -o -name 'rainbow_inventory_media_*.tar.gz.sha256' \) -mtime "+$BACKUP_RETENTION_DAYS" -delete
RESULT=success; write_status "Media archive verified and retained for ${BACKUP_RETENTION_DAYS} days."; log "result=success file=${NAME} size_bytes=${SIZE} sha256=${CHECKSUM}"
