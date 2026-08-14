# Critical production fixes

## Baseline inspected on 2026-08-03

This work is on branch `critical/production-stock-import-fixes`. The current
recovery snapshot contains 33 pending path entries that existed before this
programme continued. Those files are not staged or treated as part of this
work.

## Pre-existing workspace inventory

The recovery snapshot is stored locally in `.codex-safety/` and is intentionally
untracked. The current checkout had the following pending files before any new
critical-programme implementation. Classification describes overlap only; it
does not grant permission to stage the work.

| Classification | Files |
| --- | --- |
| Required dependency | `.gitlab-ci.yml`, `docker-compose.yml`, `frontend/nginx.conf`, `deployment/nginx/test.rainbow-fashions.in.conf`, `deployment/logrotate/`, `deployment/scripts/check_application_health.sh`, `deployment/scripts/configure_firewall_ufw.sh`, `deployment/scripts/diagnose_domain.sh`, `deployment/scripts/smoke_test_production.sh`, `deployment/scripts/wait_for_application.sh`, `deployment/systemd/rainbow-fashions.service`, `deployment/systemd/rainbow-health-watch.service`, `deployment/systemd/rainbow-health-watch.timer`, `deployment/templates/availability-alerts.template`, `deployment/tests/`, `docs/CI_CD.md`, `docs/DEPLOYMENT.md`, `docs/DEPLOYMENT_AVAILABILITY_HARDENING.md` |
| Related to this critical task | `frontend/src/pages/NewSalePage.tsx`, `frontend/src/pages/NewSalePage.test.tsx`, `frontend/src/pages/ProductsPage.tsx`, `frontend/src/pages/productEditLogic.ts`, `frontend/src/pages/productEditLogic.test.ts`, `frontend/src/pages/StockAdjustmentPage.tsx`, `frontend/src/pages/StockPage.tsx`, `frontend/src/utils/apiPayload.ts`, `docs/LIVE_FEATURE_VERIFICATION_MATRIX.md`, `docs/LIVE_UI_GAP_REPORT.md`, `docs/RELEASE_READINESS.md`, `docs/UAT_CHECKLIST.md`, `docs/live-feature-verification.md` |
| Unrelated | `backend/app/schemas/stock_scan.py`, `backend/tests/test_existing_variant_barcode_onboarding.py`, `frontend/src/components/BarcodeOnboardingDialog.tsx`, `frontend/src/components/barcodeOnboardingLogic.ts`, `frontend/src/components/barcodeOnboardingLogic.test.ts` |
| Uncertain | None identified in the current 33-file status inventory. |

The required-dependency and related files already have pending changes. Their
complete diffs must be reviewed before any additional edit. New files created
for this programme will be staged path-by-path only after validation.

### Architecture

- React/Vite is served by the frontend Nginx container.
- FastAPI exposes `/api/v1` and has request-scoped SQLAlchemy sessions.
- PostgreSQL is the persistence layer.
- `ProductVariant` is the store-scoped sellable identity. `Product.current_stock`
  and `product_inventory` are compatibility aggregates; stock changes also write
  `StockHistory` ledger rows.
- Purchase confirmation, POS sale, return, void, stock-scan confirmation, and
  authorized adjustments are transaction-based stock workflows.
- `ProductBarcode` maps scanner values to a store-scoped exact variant. A
  `StockScanSession` is a persistent draft and does not post inventory until
  confirmation.

### Existing issues identified

1. The existing product CSV importer (`ProductService.import_products`) is not
   suitable for opening stock: it accepts a direct `current_stock` field, skips
   invalid rows, and can leave an import partially applied.
2. There is no `stock_imports` domain model, immutable import preview, import
   idempotency record, mandatory import backup record, or compensating rollback
   workflow.
3. The current public endpoint is an IP address. A publicly trusted TLS
   certificate requires a DNS hostname pointing to the server. The repository
   contains a prepared `test.rainbow-fashions.in` host-level Nginx config, but a
   production certificate and DNS cannot be verified from this workspace.
4. Local Docker services are not running and production SSH authentication is
   unavailable, so manual production verification cannot be claimed.
5. Deployment documentation contains obsolete example credentials and must be
   corrected as part of a dedicated documentation review; no credentials are
   copied into this document.

## Baseline tests

Run before implementing this programme:

- Backend: `./.venv/bin/pytest -q` — 149 passed, 1 third-party Argon2
  deprecation warning.
- Frontend: `npm run test`, `npm run lint`, `npm run typecheck`, and
  `npm run build` — all passed. The production build emitted only a bundle-size
  advisory.

## Required implementation order

1. Add an isolated, strict opening-stock import domain and migration.
2. Add validated CSV preview, idempotent commit, backup gate, ledger posting,
   and compensating rollback.
3. Add import UI and workflow tests without changing the existing product
   importer semantics.
4. Correct deployment documentation and validate host-level Nginx only after
   DNS and server access are available.
5. Run the 2,000-row benchmark against an isolated test database and record
   measured, not estimated, results.

## Remaining risks

- No production data should be imported until the backup target and production
  environment are independently verified.
- Existing uncommitted changes must be reviewed and separated before release.
- HTTPS deployment remains blocked on DNS, certificate issuance, and server
  access.

## Local verification update

- The isolated Docker UAT stack was rebuilt with `TEST_ENV_MODE=docker
  ./scripts/start-test-environment.sh`. It used `rainbow_inventory_test`, ran
  migrations, and seeded controlled test data only.
- Docker-host checks returned HTTP 200 for `/health` and `/health/ready`; the
  latter verifies database connectivity. The direct `/api/health` alias is now
  implemented as the same readiness check for the requested UAT route.
- Product metadata edits remain catalogue-only. Direct `current_stock` edits
  are rejected with `STOCK_FIELDS_READ_ONLY`. Metadata and image changes now
  create immutable `product_update_audits` records.
- A first migration-backed strict opening-stock-import domain is implemented:
  store-scoped CSV validation, idempotency key and file hash, row preview,
  existing-active-variant matching, no second opening movement, explicit
  confirmation state transitions, and fail-closed backup gating.

### Commands completed

```text
cd backend && .venv/bin/pytest -q tests/test_product_metadata_update.py tests/test_health.py
10 passed

cd backend && .venv/bin/alembic heads
20260803_0039 (head)

cd frontend && npm run test -- --run src/pages/productEditLogic.test.ts
4 passed
cd frontend && npm run lint
PASS
cd frontend && npm run typecheck
PASS
```

The full import confirmation journey, compensating rollback, production backup
scripts, integration journey, 2,000-row benchmark, and deployment execution
are incomplete and must not be reported as passing.
