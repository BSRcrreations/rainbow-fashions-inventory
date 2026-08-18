#!/usr/bin/env bash
# Destructive, runner-only cleanup for the isolated Rainbow TEST/UAT database.
# It deliberately has no production mode and refuses every identity mismatch.
set -Eeuo pipefail

fail() { printf 'TEST/UAT reset: %s\n' "$1" >&2; exit 1; }

: "${DEPLOY_ENVIRONMENT:?DEPLOY_ENVIRONMENT is required}"
: "${DEPLOY_PATH:?DEPLOY_PATH is required}"
: "${COMPOSE_PROJECT_NAME:?COMPOSE_PROJECT_NAME is required}"
: "${BACKEND_ENV_FILE:?BACKEND_ENV_FILE is required}"
: "${PUBLIC_DEPLOY_URL:?PUBLIC_DEPLOY_URL is required}"
: "${TEST_OWNER_PASSWORD:?TEST_OWNER_PASSWORD must be supplied as a protected CI variable}"

[[ "$DEPLOY_ENVIRONMENT" == "test" ]] || fail 'only DEPLOY_ENVIRONMENT=test is permitted'
[[ "$DEPLOY_PATH" == "/opt/rainbow-fashions-test" ]] || fail 'unexpected deployment path'
[[ "$COMPOSE_PROJECT_NAME" == "rainbow_test" ]] || fail 'unexpected Compose project'
[[ "$BACKEND_ENV_FILE" == "/opt/rainbow-fashions-test/shared/backend.env" ]] || fail 'unexpected backend environment file'
[[ "$PUBLIC_DEPLOY_URL" == "https://test.rainbow-fashions.in" ]] || fail 'unexpected public hostname'
[[ "${CI_COMMIT_REF_PROTECTED:-true}" == "true" ]] || fail 'manual reset must run from a protected ref'
[[ "${CI_ENVIRONMENT_NAME:-staging}" == "staging" ]] || fail 'manual reset must use the staging environment'

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${script_dir}/verify_deployment_context.sh"

# This is an env_file, not a shell script: values may legally contain spaces
# or shell metacharacters. Read only the two non-secret values needed for the
# guard; PostgreSQL credentials stay inside its running TEST container.
env_value() {
  sed -n -E "s/^[[:space:]]*$1=(.*)$/\\1/p" "$BACKEND_ENV_FILE" | head -n 1
}
test_app_env="$(env_value APP_ENV)"
test_database="$(env_value POSTGRES_DB)"
[[ "$test_app_env" == "staging" ]] || fail 'APP_ENV is not staging'
[[ "$test_database" == "rainbow_test_db" ]] || fail 'database is not rainbow_test_db'

current_dir="$DEPLOY_PATH/current"
[[ -d "$current_dir" ]] || fail 'current TEST release is missing'
compose=(docker compose --env-file /dev/null -p rainbow_test -f "$current_dir/docker-compose.yml" -f "$current_dir/docker-compose.test.yml")
postgres_id="$("${compose[@]}" ps -q postgres)"
[[ -n "$postgres_id" ]] || fail 'TEST PostgreSQL container is not running'
[[ "$(docker inspect -f '{{.Name}}' "$postgres_id")" == "/rainbow_test-postgres-1" ]] || fail 'PostgreSQL container name mismatch'
[[ "$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.project" }}' "$postgres_id")" == "rainbow_test" ]] || fail 'PostgreSQL Compose label mismatch'
postgres_volume="$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Name}}{{end}}{{end}}' "$postgres_id")"
[[ "$postgres_volume" == "rainbow_test_postgres_data" ]] || fail 'PostgreSQL volume mismatch'
docker volume inspect rainbow_test_postgres_data >/dev/null || fail 'expected TEST PostgreSQL volume is unavailable'

for forbidden in inventory_db current_postgres_data rainbow_prod /opt/rainbow-fashions-prod; do
  [[ "$DEPLOY_PATH $COMPOSE_PROJECT_NAME $test_database $postgres_volume" != *"$forbidden"* ]] || fail 'a production identifier was detected in the target'
done

version_payload="$(mktemp)"
login_payload="$(mktemp)"
lookup_payload="$(mktemp)"
restore_container=''
restore_volume=''
cleanup() {
  rm -f "$version_payload" "$login_payload" "$lookup_payload"
  [[ -z "$restore_container" ]] || docker rm -f "$restore_container" >/dev/null 2>&1 || true
  [[ -z "$restore_volume" ]] || docker volume rm "$restore_volume" >/dev/null 2>&1 || true
}
trap cleanup EXIT
curl --fail --silent --show-error --max-time 15 "$PUBLIC_DEPLOY_URL/health/ready" >/dev/null
curl --fail --silent --show-error --max-time 15 "$PUBLIC_DEPLOY_URL/version" -o "$version_payload"
python3 - "$version_payload" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
if payload.get("environment") != "staging":
    raise SystemExit("TEST/UAT reset: /version did not report staging")
PY

psql_in_container() {
  docker exec -i "$postgres_id" sh -ceu '
    export PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
    exec psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"
  '
}

owner_email='uat-owner@rainbow-fashions.com'
owner_check="$(psql_in_container -Atqc "SELECT role::text || ':' || is_active::text FROM users WHERE lower(email) = lower('$owner_email')")"
[[ "$owner_check" == "OWNER:true" ]] || fail 'required active UAT Owner account is missing or not an Owner'

# Authenticate before deleting so a stale/misconfigured protected password
# cannot leave a reset complete without a usable Owner login.
python3 - <<'PY' | curl --fail --silent --show-error --max-time 15 -X POST \
  -H 'Content-Type: application/json' --data-binary @- \
  "$PUBLIC_DEPLOY_URL/api/v1/auth/login" -o "$login_payload"
import json, os
print(json.dumps({"email": "uat-owner@rainbow-fashions.com", "password": os.environ["TEST_OWNER_PASSWORD"]}))
PY
access_token="$(python3 - "$login_payload" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
if payload.get("user", {}).get("email", "").lower() != "uat-owner@rainbow-fashions.com" or payload.get("user", {}).get("role") != "OWNER":
    raise SystemExit("TEST/UAT reset: Owner login did not return the required Owner account")
print(payload["access_token"])
PY
)"

counts_sql="
SELECT concat_ws(E'\\n',
  'Products=' || (SELECT count(*) FROM products),
  'Variants=' || (SELECT count(*) FROM product_variants),
  'Barcode mappings=' || (SELECT count(*) FROM product_barcodes),
  'Shared targets=' || (SELECT count(*) FROM product_barcode_variant_targets),
  'Physical stock=' || COALESCE((SELECT sum(current_stock) FROM product_variants), 0),
  'Ledger movements=' || (SELECT count(*) FROM stock_history),
  'Cost lots=' || (SELECT count(*) FROM inventory_cost_lots),
  'Draft sessions=' || (SELECT count(*) FROM stock_scan_sessions),
  'Import sessions=' || ((SELECT count(*) FROM stock_imports) + (SELECT count(*) FROM opening_stock_imports)),
  'Sales=' || (SELECT count(*) FROM sales),
  'Purchases=' || (SELECT count(*) FROM purchases),
  'Suppliers=' || (SELECT count(*) FROM suppliers),
  'Customers=' || (SELECT count(*) FROM customers),
  'Expenses=' || (SELECT count(*) FROM expenses),
  'Categories=' || (SELECT count(*) FROM categories),
  'Brands=' || (SELECT count(*) FROM brands)
);"
pre_counts="$(psql_in_container -Atqc "$counts_sql")"
printf 'TEST/UAT reset pre-counts:\n%s\n' "$pre_counts"

# Create a fresh custom-format backup without reading credentials onto the
# runner. Validate its checksum and restore it into a network-isolated,
# disposable PostgreSQL container before the transaction below is allowed.
backup_timestamp="$(date -u '+%Y%m%d_%H%M%S')"
backup_dir="$DEPLOY_PATH/backups/database/$(date -u '+%Y/%m/%d')"
backup_file="$backup_dir/rainbow_test_uat_reset_${backup_timestamp}.dump"
backup_partial="${backup_file}.partial"
backup_checksum="${backup_file}.sha256"
postgres_image="$(docker inspect -f '{{.Config.Image}}' "$postgres_id")"
install -d -m 700 "$backup_dir"
umask 077
docker exec -i "$postgres_id" sh -ceu '
  export PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
  exec pg_dump -Fc -U "$POSTGRES_USER" -d "$POSTGRES_DB"
' > "$backup_partial"
[[ -s "$backup_partial" ]] || fail 'pg_dump produced an empty backup'
docker run --rm --network none -v "$backup_dir:/backup:ro" "$postgres_image" \
  pg_restore --list "/backup/$(basename "$backup_partial")" >/dev/null
mv "$backup_partial" "$backup_file"
backup_sha256="$(sha256sum "$backup_file" | awk '{print $1}')"
printf '%s  %s\n' "$backup_sha256" "$backup_file" > "$backup_checksum"
sha256sum --check "$backup_checksum" >/dev/null

restore_container="rainbow-test-uat-reset-restore-${backup_timestamp}"
restore_volume="rainbow_test_uat_reset_restore_${backup_timestamp}"
restore_password="$(openssl rand -hex 24)"
docker run --detach --name "$restore_container" --network none \
  --mount "type=volume,source=${restore_volume},target=/var/lib/postgresql/data" \
  --env POSTGRES_DB=rainbow_reset_restore --env POSTGRES_USER=rainbow_restore \
  --env "POSTGRES_PASSWORD=${restore_password}" "$postgres_image" >/dev/null
for _ in $(seq 1 30); do
  if docker exec "$restore_container" pg_isready -U rainbow_restore -d rainbow_reset_restore >/dev/null 2>&1; then break; fi
  sleep 1
done
docker exec "$restore_container" pg_isready -U rainbow_restore -d rainbow_reset_restore >/dev/null
docker run --rm --network none -v "$backup_dir:/backup:ro" "$postgres_image" \
  pg_restore --no-owner --no-acl --exit-on-error --file=- "/backup/$(basename "$backup_file")" |
  docker exec -i "$restore_container" sh -ceu 'export PGPASSWORD="$POSTGRES_PASSWORD"; psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null
restore_alembic="$(docker exec "$restore_container" sh -ceu 'export PGPASSWORD="$POSTGRES_PASSWORD"; psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SELECT version_num FROM alembic_version LIMIT 1"')"
[[ -n "$restore_alembic" ]] || fail 'isolated restore did not contain an Alembic version'
printf 'TEST/UAT reset backup and isolated restore verification: PASS\n'

# Reject schema drift rather than guessing at an incomplete dependency order.
# All listed tables are UAT business/catalogue, stock, barcode, document, or
# business-audit data. users, stores, roles, settings, and alembic remain out.
psql_in_container <<'SQL'
BEGIN;
DO $$
DECLARE
  reset_tables text[] := ARRAY[
    'sale_return_items', 'sale_returns', 'sale_items', 'sale_audits', 'sales',
    'stock_history', 'inventory_cost_lots', 'product_inventory',
    'product_barcode_variant_targets', 'product_barcode_audits', 'product_barcodes',
    'stock_scan_session_items', 'stock_scan_sessions',
    'opening_stock_import_barcode_groups', 'opening_stock_import_errors',
    'opening_stock_import_audits', 'opening_stock_import_rows', 'opening_stock_imports',
    'stock_import_backups', 'stock_import_rollbacks', 'stock_import_rows', 'stock_imports',
    'document_processing_jobs', 'purchase_documents', 'purchase_audits', 'purchase_items', 'purchases',
    'supplier_payments', 'suppliers', 'customer_payments', 'customers',
    'expenses', 'expense_categories', 'uploaded_files',
    'inventory_reconciliation_audits', 'product_update_audits', 'product_deletion_audits', 'stock_audit_events',
    'product_variants', 'products', 'brands', 'subcategories', 'categories'
  ];
  missing text;
  external_dependencies text;
BEGIN
  SELECT string_agg(table_name, ', ' ORDER BY table_name) INTO missing
  FROM unnest(reset_tables) AS table_name
  WHERE to_regclass('public.' || table_name) IS NULL;
  IF missing IS NOT NULL THEN
    RAISE EXCEPTION 'Reset aborted: expected business tables are missing: %', missing;
  END IF;

  SELECT string_agg(child.relname || ' -> ' || parent.relname, ', ' ORDER BY child.relname, parent.relname)
  INTO external_dependencies
  FROM pg_constraint con
  JOIN pg_class child ON child.oid = con.conrelid
  JOIN pg_namespace child_ns ON child_ns.oid = child.relnamespace
  JOIN pg_class parent ON parent.oid = con.confrelid
  JOIN pg_namespace parent_ns ON parent_ns.oid = parent.relnamespace
  WHERE con.contype = 'f'
    AND parent_ns.nspname = 'public'
    AND child_ns.nspname = 'public'
    AND parent.relname = ANY(reset_tables)
    AND NOT child.relname = ANY(reset_tables);
  IF external_dependencies IS NOT NULL THEN
    RAISE EXCEPTION 'Reset aborted: unreviewed dependent tables: %', external_dependencies;
  END IF;
END $$;

DELETE FROM sale_return_items;
DELETE FROM sale_returns;
DELETE FROM stock_history;
DELETE FROM sale_items;
DELETE FROM sale_audits;
DELETE FROM sales;
DELETE FROM opening_stock_import_barcode_groups;
DELETE FROM opening_stock_import_errors;
DELETE FROM opening_stock_import_audits;
DELETE FROM opening_stock_import_rows;
DELETE FROM opening_stock_imports;
DELETE FROM stock_import_backups;
DELETE FROM stock_import_rollbacks;
DELETE FROM stock_import_rows;
DELETE FROM stock_imports;
DELETE FROM stock_scan_session_items;
DELETE FROM stock_scan_sessions;
DELETE FROM document_processing_jobs;
DELETE FROM purchase_documents;
DELETE FROM inventory_cost_lots;
DELETE FROM purchase_audits;
DELETE FROM purchase_items;
DELETE FROM purchases;
DELETE FROM supplier_payments;
DELETE FROM suppliers;
DELETE FROM customer_payments;
DELETE FROM customers;
DELETE FROM expenses;
DELETE FROM expense_categories;
DELETE FROM uploaded_files;
DELETE FROM inventory_reconciliation_audits;
DELETE FROM product_update_audits;
DELETE FROM product_deletion_audits;
DELETE FROM stock_audit_events;
DELETE FROM product_barcode_variant_targets;
DELETE FROM product_barcode_audits;
DELETE FROM product_barcodes;
DELETE FROM product_inventory;
DELETE FROM product_variants;
DELETE FROM products;
DELETE FROM brands;
DELETE FROM subcategories;
DELETE FROM categories;
COMMIT;
SQL

post_counts="$(psql_in_container -Atqc "$counts_sql")"
printf 'TEST/UAT reset post-counts:\n%s\n' "$post_counts"
if grep -Eq '=(0|0\.0+)$' <<<"$post_counts"; then :; fi
if grep -Ev '^(Products|Variants|Barcode mappings|Shared targets|Physical stock|Ledger movements|Cost lots|Draft sessions|Import sessions|Sales|Purchases|Suppliers|Customers|Expenses|Categories|Brands)=0$' <<<"$post_counts" >/dev/null; then
  fail 'post-reset database counts are not clean'
fi

# The original token was issued before the delete. Re-login after the reset
# and make the read-only Owner/API checks with a fresh token.
python3 - <<'PY' | curl --fail --silent --show-error --max-time 15 -X POST \
  -H 'Content-Type: application/json' --data-binary @- \
  "$PUBLIC_DEPLOY_URL/api/v1/auth/login" -o "$login_payload"
import json, os
print(json.dumps({"email": "uat-owner@rainbow-fashions.com", "password": os.environ["TEST_OWNER_PASSWORD"]}))
PY
access_token="$(python3 - "$login_payload" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
if payload.get("user", {}).get("role") != "OWNER":
    raise SystemExit("TEST/UAT reset: Owner authorization failed after reset")
print(payload["access_token"])
PY
)"
for endpoint in \
  '/api/v1/products?limit=1' \
  '/api/v1/categories?limit=1' \
  '/api/v1/brands?limit=1' \
  '/api/v1/stock/history?limit=1' \
  '/api/v1/sales/catalog' \
  '/api/v1/barcodes/lookup/8905072571989'; do
  curl --fail --silent --show-error --max-time 15 \
    -H "Authorization: Bearer $access_token" "$PUBLIC_DEPLOY_URL$endpoint" -o "$lookup_payload"
done
python3 - "$lookup_payload" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
if payload.get("status") != "AVAILABLE":
    raise SystemExit("TEST/UAT reset: known UAT barcode did not resolve as AVAILABLE")
PY

alembic_version="$(psql_in_container -Atqc 'SELECT version_num FROM alembic_version LIMIT 1')"
[[ -n "$alembic_version" ]] || fail 'Alembic version is missing'
status_file="$DEPLOY_PATH/backups/status/latest-test-uat-reset.json"
python3 - "$status_file" "$alembic_version" "$post_counts" <<'PY'
import json, os, sys
from pathlib import Path
path = Path(sys.argv[1])
counts = dict(line.split("=", 1) for line in sys.argv[3].splitlines())
payload = {
    "status": "SUCCESS",
    "environment": "test",
    "database": "rainbow_test_db",
    "alembic_version": sys.argv[2],
    "post_reset_counts": counts,
    "production_touched": "NO",
}
temporary = path.with_suffix(path.suffix + ".partial")
temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
os.chmod(temporary, 0o600)
temporary.replace(path)
PY
printf 'TEST/UAT reset: PASS (database=rainbow_test_db, alembic=%s)\n' "$alembic_version"
