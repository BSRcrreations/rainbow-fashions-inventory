# Inventory UAT environment

This environment is isolated from production. It uses a separate Compose project,
database, ports, Docker volumes, uploads, and JWT secret. Never point any UAT
command at `rainbow_inventory`, the Contabo server, or a production hostname.

## Branch workflow

Work moves in this order:

```text
feature branch -> shop-inventory -> test/inventory-uat -> main
```

`test/inventory-uat` is for owner acceptance testing only. Do not merge it into
`main` automatically.

## Create local-only UAT configuration

These files are ignored by Git:

```bash
cp backend/.env.test.example backend/.env.test
cp frontend/.env.test.example frontend/.env.test
chmod 600 backend/.env.test frontend/.env.test
```

In `backend/.env.test`, set a strong **testing-only** database password, JWT
secret, and `UAT_TEST_PASSWORD`. Keep these values away from production and do
not reuse the production deletion-password hash. The deterministic UAT accounts
all use the local `UAT_TEST_PASSWORD` value:

| Account | Email | Role |
| --- | --- | --- |
| Owner | `owner.uat@rainbow.test` | OWNER |
| Inventory staff | `inventory.uat@rainbow.test` | STAFF |
| Cashier | `cashier.uat@rainbow.test` | STAFF |

## Start, reset, and stop

Docker is the recommended option. It creates only these isolated resources:

| Resource | Value |
| --- | --- |
| Compose project | `rainbow-inventory-test` |
| PostgreSQL container | `rainbow-test-db` |
| Backend container | `rainbow-test-backend` |
| Frontend container | `rainbow-test-frontend` |
| Database | `rainbow_inventory_test` |
| PostgreSQL host port | `127.0.0.1:5433` |
| Backend port | `127.0.0.1:8001` |
| Frontend port | `http://127.0.0.1:5174` |
| Volumes | `rainbow_test_postgres_data`, `rainbow_test_uploads` |

```bash
scripts/start-test-environment.sh
scripts/reset-test-database.sh
scripts/stop-test-environment.sh
```

The reset command requires typing `RESET rainbow_inventory_test` when run in a
terminal. It refuses to proceed unless `APP_ENV=testing`, the name ends in
`_test`, and the host does not look like production. It drops **only the test
schema**, applies Alembic migrations, then reseeds UAT data.

For direct development rather than Docker, first run an isolated PostgreSQL
database on `127.0.0.1:5433`, then use:

```bash
TEST_ENV_MODE=direct scripts/start-test-environment.sh
TEST_ENV_MODE=direct scripts/reset-test-database.sh
TEST_ENV_MODE=direct scripts/stop-test-environment.sh
```

The direct frontend uses `frontend/.env.test` and calls
`http://127.0.0.1:8001/api/v1`. The normal development ports (`5173`, `8000`)
are not used.

## Deterministic seed data

The reset and seed commands create the following UAT-only data:

- Categories: Leggings, Bras, Panties
- Brands: Prisma, Fly Birds, Twin Birds, Lovable
- Products: Full Leggings for Prisma and Fly Birds
- Variants for each product: S, M, L, XL, 2XL, 3XL; colour Assorted
- Every variant starts at 20 units. Each base product is 120 units, matching
  the sum of its six variants.
- Test-only barcodes and SKUs start with `UAT-`. Real manufacturer barcodes can
  be assigned during UAT because this is a separate database.

Opening stock has a matching `OPENING_STOCK` inventory history record and cost
lot. Subsequent stock tests must use the normal adjustment, scan, and sale
workflows rather than editing stock columns.

## Automated validation

With the local UAT environment configuration present:

```bash
scripts/run-all-tests.sh
```

This runs backend tests, checks there is exactly one Alembic head, then runs
frontend tests, lint, typecheck, and production build. Use the test database
only for database-backed acceptance tests.

## Owner UAT checklist

### Products and variants

- [ ] Products show category, brand, SKU, barcode, purchase cost, MRP, selling price, and stock.
- [ ] Prisma and Fly Birds Full Leggings each show S, M, L, XL, 2XL, and 3XL separately.
- [ ] Base product stock equals the sum of its displayed variants.
- [ ] Products can be found by UAT barcode, category, brand, and size.
- [ ] Editing stock opens Stock Adjustment; it does not overwrite stock directly.

### Stock and barcode entry

- [ ] Category-first scan flow filters products to the selected category and brand.
- [ ] Unknown barcode keeps selected category and brand but allows editing and exact-variant creation.
- [ ] Scan the same `UAT-MFG-...` barcode five times: one mapping, one draft row, scanned quantity five, no duplicate error.
- [ ] Confirmed stock increases once; retrying confirmation does not add it again.
- [ ] A barcode mapped to another variant shows a useful conflict without changing stock.
- [ ] Leading-zero test barcodes keep their leading zeroes.
- [ ] Reset preview covers only selected UAT variants; reset makes their stock zero while retaining products and mappings.
- [ ] Adjustment in, adjustment out, and counted quantity each create an append-only transaction.

### Sales

- [ ] Choose or scan Prisma XL: only XL enters the cart and only XL stock decreases.
- [ ] Completing a sale with 0%, 5%, 10%, 15%, and decimal discounts calculates correctly.
- [ ] A subtotal of ₹998.00 with 10% discount produces ₹99.80 discount and ₹898.20 total.
- [ ] A percentage above 100 is rejected once with a useful error.
- [ ] Voiding the sale restores only its exact variant stock and retains an audit trail.

## Promotion to main

After owner UAT approval and a passing GitLab pipeline, create a merge request
in GitLab with:

```text
Source branch: test/inventory-uat
Target branch: main
```

Require code review, migration review, owner UAT approval, a production backup,
and a rollback plan. Do not merge automatically.

## Production deployment preparation

Before any later `main` deployment:

1. Record the current production commit and image/artifact tag.
2. Run the existing production PostgreSQL backup procedure and verify it.
3. Review each Alembic migration and run it once in UAT.
4. Deploy through the protected production pipeline.
5. Smoke-test `/`, `/health`, `/health/ready`, login, one read-only product list,
   and one read-only sales list.
6. If a deployment fails, stop at the last healthy artifact, restore the prior
   application image, and use the verified database backup only when a database
   rollback is explicitly necessary.

Stock reset is never a deployment step. It remains an explicit owner business
action, and it must never be run as part of production rollout or rollback.
