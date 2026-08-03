#!/usr/bin/env bash
# Restore the newest verified dump into an isolated disposable PostgreSQL
# container. It has no public port or production network attachment.
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib_backup.sh"

backup_require_command docker
backup_require_command python3
backup_init_log database-restore-test.log
backup_lock restore-test

latest_dump="$(find "${RAINBOW_BACKUP_ROOT}/database" -type f -name 'rainbow_inventory_*.dump' -print 2>/dev/null | sort | tail -n 1)"
[[ -n "$latest_dump" && -s "$latest_dump" ]] || backup_die "No local database backup is available for restore testing."
backup_check_sha256 "$latest_dump" || backup_die "The selected backup checksum is invalid."

image="$(backup_postgres_image)"
backup_dir="$(dirname "$latest_dump")"
backup_name="$(basename "$latest_dump")"
timestamp="$(backup_timestamp)"
container="rainbow-restore-test-${timestamp}"
volume="rainbow_restore_test_${timestamp}"
restore_password="$(openssl rand -hex 24 2>/dev/null || date +%s%N | shasum | cut -c1-48)"
report_dir="${RAINBOW_BACKUP_ROOT}/restore-tests/$(date -u '+%Y/%m')"
report="${report_dir}/restore_test_${timestamp}.json"
started_epoch="$(date +%s)"

mkdir -p "$report_dir"
chmod 700 "$report_dir"
umask 077
cleanup() {
  local cleanup_status=SUCCESS
  docker rm -f "$container" >/dev/null 2>&1 || cleanup_status=PARTIAL
  docker volume rm "$volume" >/dev/null 2>&1 || cleanup_status=PARTIAL
  if [[ -f "$report" ]]; then
    python3 - "$report" "$cleanup_status" <<'PY'
import json
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
payload = json.loads(path.read_text(encoding='utf-8'))
payload['cleanup_status'] = sys.argv[2]
temporary = path.with_suffix(path.suffix + '.partial')
temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
os.chmod(temporary, 0o600)
temporary.replace(path)
PY
  fi
}
trap cleanup EXIT
write_failure() {
  local exit_code="$1"
  backup_write_json "$report" "backup_filename=${backup_name}" "checksum_result=SUCCESS" \
    "restore_start=$(backup_now)" "restore_duration_seconds=$(( $(date +%s) - started_epoch ))" \
    "cleanup_status=PENDING" "result=FAILED" "error=Restore test failed; inspect ${BACKUP_LOG_FILE}" "exit_code=${exit_code}"
  backup_write_json "${RAINBOW_BACKUP_STATUS_DIR}/latest-database-restore-test.json" \
    "timestamp=$(backup_now)" "status=FAILED" "report_path=${report}" "backup_filename=${backup_name}" "exit_code=${exit_code}"
  backup_log "database_restore_test_failed backup=${backup_name} exit_code=${exit_code}"
}
trap 'code=$?; write_failure "$code"; exit "$code"' ERR

docker run --detach --name "$container" --network none \
  --mount "type=volume,source=${volume},target=/var/lib/postgresql/data" \
  --env POSTGRES_DB=rainbow_restore_test --env POSTGRES_USER=rainbow_restore \
  --env "POSTGRES_PASSWORD=${restore_password}" "$image" >/dev/null
for _ in $(seq 1 30); do
  if docker exec "$container" pg_isready -U rainbow_restore -d rainbow_restore_test >/dev/null 2>&1; then break; fi
  sleep 1
done
docker exec "$container" pg_isready -U rainbow_restore -d rainbow_restore_test >/dev/null

docker run --rm --network none -v "${backup_dir}:/backup:ro" "$image" \
  pg_restore --no-owner --no-acl --exit-on-error --file=- "/backup/${backup_name}" |
  docker exec -i "$container" sh -ceu 'export PGPASSWORD="$POSTGRES_PASSWORD"; psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

table_counts="$(docker exec -i "$container" sh -ceu '
  export PGPASSWORD="$POSTGRES_PASSWORD"
  for table in stores users products product_variants product_barcodes product_inventory stock_history sales purchases; do
    printf "%s=" "$table"
    psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SELECT count(*) FROM ${table}"
  done
')"
alembic_version="$(docker exec -i "$container" sh -ceu 'export PGPASSWORD="$POSTGRES_PASSWORD"; psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SELECT version_num FROM alembic_version LIMIT 1"')"
foreign_key_violations="$(docker exec -i "$container" sh -ceu 'export PGPASSWORD="$POSTGRES_PASSWORD"; psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SELECT count(*) FROM (SELECT conrelid::regclass::text AS table_name, conname FROM pg_constraint WHERE contype = '\''f'\'') constraints"')"
duration="$(( $(date +%s) - started_epoch ))"

backup_write_json "$report" \
  "backup_filename=${backup_name}" "checksum_result=SUCCESS" "restore_start=$(backup_now)" \
  "restore_duration_seconds=${duration}" "postgresql_version=$(docker exec "$container" psql --version)" \
  "tables_validated=stores,users,products,product_variants,product_barcodes,product_inventory,stock_history,sales,purchases" \
  "row_counts=${table_counts}" "alembic_version=${alembic_version}" "foreign_keys_checked=${foreign_key_violations}" "cleanup_status=PENDING" "result=SUCCESS"
backup_write_json "${RAINBOW_BACKUP_STATUS_DIR}/latest-database-restore-test.json" \
  "timestamp=$(backup_now)" "status=SUCCESS" "report_path=${report}" \
  "backup_filename=${backup_name}" "duration_seconds=${duration}" "row_counts=${table_counts}"
backup_log "database_restore_test_succeeded backup=${backup_name} duration_seconds=${duration}"
