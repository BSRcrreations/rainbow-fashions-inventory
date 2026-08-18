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

# The protected file is intentionally sourced only in this process.  Do not
# print it or enable shell tracing in this script.
# shellcheck source=/dev/null
source "$BACKEND_ENV_FILE"
[[ "${APP_ENV:-}" == "staging" ]] || fail 'APP_ENV is not staging'
[[ "${POSTGRES_DB:-}" == "rainbow_test_db" ]] || fail 'database is not rainbow_test_db'
[[ -n "${POSTGRES_USER:-}" && -n "${POSTGRES_PASSWORD:-}" ]] || fail 'PostgreSQL credentials are incomplete'

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
  [[ "$DEPLOY_PATH $COMPOSE_PROJECT_NAME $POSTGRES_DB $postgres_volume" != *"$forbidden"* ]] || fail 'a production identifier was detected in the target'
done

version_payload="$(mktemp)"
login_payload="$(mktemp)"
lookup_payload="$(mktemp)"
trap 'rm -f "$version_payload" "$login_payload" "$lookup_payload"' EXIT
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

# Reuse the hardened backup and isolated restore drill.  Both tools only see
# the TEST Compose project and write below the TEST deployment root.
export RAINBOW_APP_ROOT="$DEPLOY_PATH"
export RAINBOW_CURRENT_DIR="$current_dir"
export RAINBOW_SHARED_DIR="$DEPLOY_PATH/shared"
export RAINBOW_BACKEND_ENV="$BACKEND_ENV_FILE"
export RAINBOW_BACKUP_ROOT="$DEPLOY_PATH/backups"
export RAINBOW_BACKUP_STATUS_DIR="$DEPLOY_PATH/backups/status"
export RAINBOW_COMPOSE_PROJECT=rainbow_test
"${script_dir}/backup_postgres.sh"
"${script_dir}/test_database_restore.sh"

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
