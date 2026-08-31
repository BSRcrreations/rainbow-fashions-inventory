# TEST to production catalog migration

`backend/scripts/test_to_production_migration.py` is the only supported tool
for promoting the approved TEST catalog. It is not an Alembic/schema migration
and it never copies primary keys, users, passwords, sales, purchases, expenses,
sessions, stock ledger history, cost lots, corrections, audit history, or
Alembic metadata.

The package contains a generated package ID, source TEST Git SHA, UTC export
timestamp, catalog counts, mapping count, approved physical pieces, cost
valuation, canonical content hash, file hashes, and only catalog facts. It is
written as `manifest.json`, `catalog.json`, and `checksums.sha256`; no database
URL or credential is persisted.

## Build the package

The default mode is catalog only:

```bash
cd backend
.venv/bin/python scripts/test_to_production_migration.py export \
  --source-database-url "$TEST_DATABASE_URL" \
  --source-store-code "$TEST_STORE_CODE" \
  --source-sha "$GIT_SHA" \
  --output-dir /secure/migration-packages
```

`--source-database-url` must resolve to `rainbow_test_db`. For
`CATALOG_AND_OPENING_STOCK`, supply an Owner-reviewed UTF-8 CSV with exactly
`variant_key,quantity`; it must name every exact variant once and quantities
must be zero or positive. The source ledger is never exported. The result uses
only that approved final quantity and the variant's approved source cost.

## Dry-run first

```bash
.venv/bin/python scripts/test_to_production_migration.py dry-run \
  --package-dir /secure/migration-packages/TTP-... \
  --target-database-url "$PRODUCTION_DATABASE_URL" \
  --target-store-code "$PRODUCTION_STORE_CODE"
```

Dry-run checks checksums and uses stable keys (category/brand/product family or
SKU, then product + exact size + colour). It reports creates, exact existing
matches, conflicts, barcode groups/targets to add, stock quantities, pieces,
and valuation. It has no write path. A product, exact variant, price, primary
barcode, or shared-barcode target mismatch is a conflict: it is never silently
overwritten.

The package ID is persisted in `catalog_migration_imports` per production
store. Replaying a completed package returns an idempotent result; it cannot
create duplicate catalog rows, barcode targets, or opening stock.

## Gated production schema expectation

The approved production schema target is `20260824_0044`. A production
database currently stamped `20260804_0040` must follow exactly:

```text
20260804_0040 → 20260814_0041 → 20260814_0042 → 20260815_0043 → 20260824_0044
```

Revision `0044` only creates `catalog_migration_imports` and its two indexes.
It does not update, backfill, delete, reset, or otherwise alter catalog rows,
barcode mappings, variant stock, cost lots, or inventory ledger entries.

Do not run Gate 3 to apply this path until Gate 2 has passed. The immutable
order is:

```text
Gate 2 PASS → Gate 3 → Gate 4 → Smoke Test → Stock Reset → TEST-to-PRODUCTION migration
```

## Production execution (not part of this change)

The `execute` subcommand is deliberately separate. It aborts unless the live
database is `inventory_db`, `COMPOSE_PROJECT_NAME=current`,
`POSTGRES_DATA_VOLUME=current_postgres_data`, and a local evidence JSON marks
Gate 2, Gate 3, Gate 4, production smoke test, and initial-stock reset as
`PASS`. In opening-stock mode it additionally requires an active Owner in the
target store and the exact typed authorization:

```text
OWNER APPROVED OPENING STOCK <package-id>
```

It verifies target variant stock is zero before posting. Catalog and mappings
are created in one transaction. Each approved non-zero quantity is then posted
through `OpeningStockImportService.post_migration_opening_stock`, creating an
`OPENING_STOCK` movement and an opening cost lot with reference
`TEST-CATALOG-MIGRATION:<package-id>`. The transaction verifies that imported
pieces equal both the generated movement total and the ledger total. Any error
rolls back the entire package; the corrected package can be dry-run and retried.
