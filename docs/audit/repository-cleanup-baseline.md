# Repository cleanup baseline

## Scope and safety

- **Assessment date:** 2026-08-03
- **Repository source:** `origin/main`, fetched before assessment without changing the user checkout.
- **Commit inspected:** `54cf706a30c0e30c8db18a82f389a66eed16caee` (`Merge pull request #14 from BSRcrreations/test/inventory-uat`).
- **Audit branch:** `audit/repository-cleanup-baseline`, created from the fetched `origin/main`.
- **Original workspace state:** branch `test/inventory-uat` at `3489d04 feat(stock): add guarded opening stock imports`; two untracked user-owned paths were present: `.codex-safety/` and `test/inventory-uat`.
- **Isolation:** all commands and the only change in this commit were made in a separate worktree. No existing user change was staged, overwritten, reset, stashed, or committed.
- **Redaction:** this report deliberately omits environment-file paths and contents, secret values, database-dump paths and contents, runtime-upload paths, and the invoice fixture path. These exclusions are required safety controls.

## Tracked tree inventory

`git ls-files` reported **376** tracked paths. The safe, path-level inventory below contains **365** paths. The remaining **11** tracked paths are intentionally withheld: six environment files, two database dumps, two runtime-upload placeholders, and one invoice fixture. This is a complete count reconciliation; no withheld content was opened or copied into this report.

```text
    .gitignore
    .gitlab-ci.yml
    AUDIT/README.md
    AUDIT/android.md
    AUDIT/backend.md
    AUDIT/bugs.md
    AUDIT/database.md
    AUDIT/deployment.md
    AUDIT/frontend.md
    AUDIT/security.md
    BARCODE_FEATURE_README.md
    README.md
    TODO.md
    apply_barcode_feature.py
    backend/Dockerfile
    backend/alembic.ini
    backend/alembic/env.py
    backend/alembic/versions/.gitkeep
    backend/alembic/versions/20260716_0001_add_product_image_url.py
    backend/alembic/versions/20260717_0002_add_gst_hsn_to_products.py
    backend/alembic/versions/20260718_0002_sales_and_product_hierarchy.py
    backend/alembic/versions/20260718_0003_inventory_movement_reasons.py
    backend/alembic/versions/20260718_0004_backfill_stock_references.py
    backend/alembic/versions/20260718_0005_optional_product_variants.py
    backend/alembic/versions/20260724_0006_sale_edit_returns_voids.py
    backend/alembic/versions/20260724_0007_add_sale_correction_movement_types.py
    backend/alembic/versions/20260727_0008_purchase_review_fields.py
    backend/alembic/versions/20260727_0009_purchase_document_jobs.py
    backend/alembic/versions/20260727_0010_purchase_details_workflow.py
    backend/alembic/versions/20260727_0011_remove_mock_purchase_records.py
    backend/alembic/versions/20260727_0012_product_date_barcode_scan.py
    backend/alembic/versions/20260728_0013_merge.py
    backend/alembic/versions/20260728_0013_purchase_discount_management.py
    backend/alembic/versions/20260728_0013_purchase_item_classification_and_tenancy.py
    backend/alembic/versions/20260728_0014_safe_product_bulk_delete.py
    backend/alembic/versions/20260728_0015_product_store_scope.py
    backend/alembic/versions/20260728_0016_reconcile_purchase_discount_schema.py
    backend/alembic/versions/20260728_0017_secure_transaction_deletion.py
    backend/alembic/versions/20260728_0018_catalog_store_scope.py
    backend/alembic/versions/20260728_0019_purchase_invoice_tax_rate.py
    backend/alembic/versions/20260728_0020_repair_store_scope_columns.py
    backend/alembic/versions/20260728_0021_repair_product_test_data_flag.py
    backend/alembic/versions/20260729_0022_variant_level_inventory.py
    backend/alembic/versions/20260729_0023_backfill_sellable_variants.py
    backend/alembic/versions/20260729_0024_allocate_legacy_variant_stock.py
    backend/alembic/versions/20260729_0025_stock_scan_sessions.py
    backend/alembic/versions/20260729_0026_barcode_mappings_and_packages.py
    backend/alembic/versions/20260729_0027_stock_scan_barcode_row_key.py
    backend/alembic/versions/20260729_0028_stock_scan_onboarding_defaults.py
    backend/alembic/versions/20260729_0029_repair_stamped_classification_schema.py
    backend/alembic/versions/20260729_0030_seed_leggings_opening_stock.py
    backend/alembic/versions/20260730_0031_brand_logos.py
    backend/alembic/versions/20260730_0032_repair_product_variant_timestamps.py
    backend/alembic/versions/20260802_0033_stock_transaction_corrections.py
    backend/alembic/versions/20260802_0034_sale_checkout_discount_fields.py
    backend/alembic/versions/20260802_0035_stock_reset_audit.py
    backend/alembic/versions/20260803_0036_barcode_transfer_audit_metadata.py
    backend/alembic/versions/20260803_0037_business_accounts_expenses_reports.py
    backend/app/__init__.py
    backend/app/ai/__init__.py
    backend/app/ai/base.py
    backend/app/ai/factory.py
    backend/app/ai/invoice_parser.py
    backend/app/ai/local_ocr.py
    backend/app/ai/mock_ocr.py
    backend/app/api/__init__.py
    backend/app/api/deps.py
    backend/app/api/routes/__init__.py
    backend/app/api/routes/auth.py
    backend/app/api/routes/brands.py
    backend/app/api/routes/categories.py
    backend/app/api/routes/customers.py
    backend/app/api/routes/dashboard.py
    backend/app/api/routes/expenses.py
    backend/app/api/routes/products.py
    backend/app/api/routes/purchase_documents.py
    backend/app/api/routes/purchases.py
    backend/app/api/routes/reports.py
    backend/app/api/routes/sales.py
    backend/app/api/routes/security.py
    backend/app/api/routes/stock.py
    backend/app/api/routes/stock_scan.py
    backend/app/api/routes/subcategories.py
    backend/app/api/routes/suppliers.py
    backend/app/core/__init__.py
    backend/app/core/config.py
    backend/app/core/exceptions.py
    backend/app/core/logging.py
    backend/app/core/security.py
    backend/app/core/test_password.py
    backend/app/core/testing.py
    backend/app/database/__init__.py
    backend/app/database/base.py
    backend/app/database/session.py
    backend/app/main.py
    backend/app/models/__init__.py
    backend/app/models/brand.py
    backend/app/models/category.py
    backend/app/models/customer.py
    backend/app/models/destructive_action.py
    backend/app/models/enums.py
    backend/app/models/expense.py
    backend/app/models/product.py
    backend/app/models/product_barcode.py
    backend/app/models/product_deletion_audit.py
    backend/app/models/product_inventory.py
    backend/app/models/product_variant.py
    backend/app/models/purchase.py
    backend/app/models/purchase_audit.py
    backend/app/models/purchase_document.py
    backend/app/models/purchase_item.py
    backend/app/models/sale.py
    backend/app/models/stock_audit_event.py
    backend/app/models/stock_history.py
    backend/app/models/stock_scan.py
    backend/app/models/store.py
    backend/app/models/subcategory.py
    backend/app/models/supplier.py
    backend/app/models/uploaded_file.py
    backend/app/models/user.py
    backend/app/repositories/__init__.py
    backend/app/repositories/base.py
    backend/app/repositories/business.py
    backend/app/repositories/catalog.py
    backend/app/repositories/product.py
    backend/app/repositories/purchase.py
    backend/app/repositories/sale.py
    backend/app/repositories/stock.py
    backend/app/schemas/__init__.py
    backend/app/schemas/auth.py
    backend/app/schemas/backup.py
    backend/app/schemas/brand.py
    backend/app/schemas/category.py
    backend/app/schemas/common.py
    backend/app/schemas/customer.py
    backend/app/schemas/dashboard.py
    backend/app/schemas/expense.py
    backend/app/schemas/product.py
    backend/app/schemas/purchase.py
    backend/app/schemas/report.py
    backend/app/schemas/sale.py
    backend/app/schemas/security.py
    backend/app/schemas/stock.py
    backend/app/schemas/stock_scan.py
    backend/app/schemas/subcategory.py
    backend/app/schemas/supplier.py
    backend/app/services/__init__.py
    backend/app/services/auth_service.py
    backend/app/services/backup_status_service.py
    backend/app/services/business_service.py
    backend/app/services/catalog_service.py
    backend/app/services/dashboard_service.py
    backend/app/services/deletion_security_service.py
    backend/app/services/destructive_action_service.py
    backend/app/services/discount_calculator.py
    backend/app/services/file_service.py
    backend/app/services/product_deletion_service.py
    backend/app/services/product_service.py
    backend/app/services/purchase_document_service.py
    backend/app/services/purchase_service.py
    backend/app/services/report_service.py
    backend/app/services/sale_discount.py
    backend/app/services/sale_service.py
    backend/app/services/stock_scan_service.py
    backend/app/services/stock_service.py
    backend/app/utils/__init__.py
    backend/pytest.ini
    backend/requirements.txt
    backend/scripts/bootstrap_test_database.py
    backend/scripts/seed_test_data.py
    backend/test_password.py
    backend/tests/test_backup_status_service.py
    backend/tests/test_batch_barcodes.py
    backend/tests/test_deletion_security_service.py
    backend/tests/test_destructive_action_service.py
    backend/tests/test_existing_variant_barcode_onboarding.py
    backend/tests/test_health.py
    backend/tests/test_local_ocr.py
    backend/tests/test_model_configuration.py
    backend/tests/test_product_deletion_service.py
    backend/tests/test_product_metadata_update.py
    backend/tests/test_purchase_discount_calculator.py
    backend/tests/test_sale_discount.py
    backend/tests/test_stage1_validation.py
    backend/tests/test_stock_corrections.py
    backend/tests/test_stock_reset_service.py
    backend/tests/test_testing_environment.py
    database/README.md
    database/migrations/001_add_manager_role.sql
    database/queries/inspect_tables.sql
    database/schema.sql
    database/seed.sql
    deployment/nginx/rainbow-fashions.conf
    deployment/nginx/test.rainbow-fashions.in.conf
    deployment/scripts/apply_production_hardening.sh
    deployment/scripts/backup_media.sh
    deployment/scripts/backup_postgres.sh
    deployment/scripts/backup_uploads.sh
    deployment/scripts/check_backup_health.sh
    deployment/scripts/generate_backup_evidence_report.sh
    deployment/scripts/lib_backup.sh
    deployment/scripts/monitor_backup_disk.sh
    deployment/scripts/prepare_upload_backup.sh
    deployment/scripts/prune_local_backups.sh
    deployment/scripts/prune_offsite_backups.sh
    deployment/scripts/restore_postgres.sh
    deployment/scripts/test_backup_restore.sh
    deployment/scripts/test_database_restore.sh
    deployment/scripts/test_upload_restore.sh
    deployment/scripts/upload_backups_offsite.sh
    deployment/systemd/rainbow-backup-disk-monitor.service
    deployment/systemd/rainbow-backup-disk-monitor.timer
    deployment/systemd/rainbow-backup-health.service
    deployment/systemd/rainbow-backup-health.timer
    deployment/systemd/rainbow-backup-restore-test.service
    deployment/systemd/rainbow-backup-restore-test.timer
    deployment/systemd/rainbow-backup-retention.service
    deployment/systemd/rainbow-backup-retention.timer
    deployment/systemd/rainbow-database-backup.service
    deployment/systemd/rainbow-database-backup.timer
    deployment/systemd/rainbow-media-backup.service
    deployment/systemd/rainbow-media-backup.timer
    deployment/systemd/rainbow-offsite-backup.service
    deployment/systemd/rainbow-offsite-backup.timer
    deployment/templates/README.md
    deployment/templates/backend.env.production.example
    deployment/templates/backup-alerts.env.example
    deployment/templates/backup-offsite.env.example
    deployment/templates/backup-offsite.md
    deployment/templates/backup.env.example
    docker-compose.test.yml
    docker-compose.yml
    docs/API.md
    docs/ARCHITECTURE.md
    docs/CI_CD.md
    docs/DATA_PROTECTION_BACKUP_RESTORE.md
    docs/DEPLOYMENT.md
    docs/DESIGN_SYSTEM.md
    docs/INSTALLATION.md
    docs/INVENTORY_UAT.md
    docs/LIVE_FEATURE_VERIFICATION_MATRIX.md
    docs/LIVE_UI_GAP_REPORT.md
    docs/MODULES.md
    docs/OCR_INTERFACE.md
    docs/RELEASE_READINESS.md
    docs/STOCK_RESET_AND_VARIANT_WORKFLOWS.md
    docs/TEST_HOSTNAME_ROLLOUT.md
    docs/UAT_CHECKLIST.md
    docs/audit/backend.md
    docs/audit/bugs.md
    docs/audit/frontend.md
    docs/audit/purchase-workflow-phase-1.md
    docs/backup-recovery-current-state.md
    docs/backup-recovery-runbook.md
    docs/database-migration.md
    frontend/Dockerfile
    frontend/Dockerfile.test
    frontend/eslint.config.js
    frontend/index.html
    frontend/nginx.conf
    frontend/nginx.test.conf
    frontend/package-lock.json
    frontend/package.json
    frontend/postcss.config.js
    frontend/public/icon.svg
    frontend/public/manifest.webmanifest
    frontend/public/sw.js
    frontend/src/App.tsx
    frontend/src/api/client.ts
    frontend/src/api/queryClient.ts
    frontend/src/components/BarcodeLabelDialog.tsx
    frontend/src/components/BarcodeOnboardingDialog.tsx
    frontend/src/components/BarcodeScannerInput.tsx
    frontend/src/components/BatchBarcodeDialog.test.ts
    frontend/src/components/BatchBarcodeDialog.tsx
    frontend/src/components/BulkBarcodeTransferDialog.tsx
    frontend/src/components/CatalogManager.tsx
    frontend/src/components/ConfirmDialog.tsx
    frontend/src/components/DeletePasswordDialog.tsx
    frontend/src/components/Dialog.test.ts
    frontend/src/components/Dialog.tsx
    frontend/src/components/EmptyState.tsx
    frontend/src/components/ErrorBoundary.tsx
    frontend/src/components/ErrorState.tsx
    frontend/src/components/HighlightText.tsx
    frontend/src/components/LoadingState.tsx
    frontend/src/components/PageHeader.tsx
    frontend/src/components/StatCard.tsx
    frontend/src/components/StatusBadge.tsx
    frontend/src/components/ToastProvider.tsx
    frontend/src/components/barcodeOnboardingLogic.test.ts
    frontend/src/components/barcodeOnboardingLogic.ts
    frontend/src/components/barcodeTransferLogic.test.ts
    frontend/src/components/barcodeTransferLogic.ts
    frontend/src/components/ui/button.tsx
    frontend/src/components/ui/card.tsx
    frontend/src/hooks/useAuth.tsx
    frontend/src/hooks/useDebouncedValue.ts
    frontend/src/layouts/AppLayout.tsx
    frontend/src/lib/utils.ts
    frontend/src/main.tsx
    frontend/src/pages/BrandsPage.tsx
    frontend/src/pages/CategoriesPage.tsx
    frontend/src/pages/CustomersPage.tsx
    frontend/src/pages/DashboardPage.tsx
    frontend/src/pages/EditSalePage.tsx
    frontend/src/pages/ExpensesPage.tsx
    frontend/src/pages/LoginPage.tsx
    frontend/src/pages/NewSalePage.test.tsx
    frontend/src/pages/NewSalePage.tsx
    frontend/src/pages/ProductsPage.tsx
    frontend/src/pages/PurchaseDetailPage.tsx
    frontend/src/pages/PurchasesPage.tsx
    frontend/src/pages/ReportsPage.tsx
    frontend/src/pages/SalesDashboardPage.tsx
    frontend/src/pages/SalesHistoryPage.tsx
    frontend/src/pages/SalesPage.tsx
    frontend/src/pages/SecuritySettingsPage.tsx
    frontend/src/pages/StockAdjustmentPage.tsx
    frontend/src/pages/StockPage.tsx
    frontend/src/pages/StockScanPage.test.tsx
    frontend/src/pages/StockScanPage.tsx
    frontend/src/pages/SuppliersPage.tsx
    frontend/src/pages/newSaleCard.ts
    frontend/src/pages/newSaleLogic.ts
    frontend/src/pages/productEditLogic.test.ts
    frontend/src/pages/productEditLogic.ts
    frontend/src/pages/saleDiscount.test.ts
    frontend/src/pages/saleDiscount.ts
    frontend/src/registerServiceWorker.ts
    frontend/src/routes/ProtectedRoute.tsx
    frontend/src/stores/appStore.ts
    frontend/src/styles.css
    frontend/src/theme/tokens.ts
    frontend/src/types/index.ts
    frontend/src/utils/format.ts
    frontend/src/utils/product.ts
    frontend/src/utils/purchaseDiscount.ts
    frontend/src/vite-env.d.ts
    frontend/tailwind.config.js
    frontend/tsconfig.json
    frontend/vite.config.ts
    mobile/App.tsx
    mobile/README.md
    mobile/app.json
    mobile/package.json
    mobile/tsconfig.json
    scripts/_test_env.sh
    scripts/database/_common.sh
    scripts/database/backup_remote_database.sh
    scripts/database/check_database_environment.sh
    scripts/database/clear_production_data.sh
    scripts/database/database-migration.env.example
    scripts/database/export_local_database.sh
    scripts/database/export_local_schema.sh
    scripts/database/import_remote_database.sh
    scripts/database/migrate_database.sh
    scripts/database/rollback_remote_database.sh
    scripts/database/upload_database_dump.sh
    scripts/database/verify_database_import.sh
    scripts/reset-test-database.sh
    scripts/run-all-tests.sh
    scripts/seed-test-data.sh
    scripts/start-test-environment.sh
    scripts/stop-test-environment.sh
```

## Module map

| Area | Inventory |
| --- | --- |
| Backend | `backend/app/`: FastAPI application, API routes, core configuration/security, database session/base, SQLAlchemy models, repositories, schemas, services, AI/OCR integration, and utilities. `backend/scripts/` holds test-data/bootstrap helpers. |
| Frontend | `frontend/src/`: Vite/React/TypeScript SPA with pages, reusable components, app layout, API client/query client, hooks, store, routes, styles, theme, and utility code. |
| Mobile scaffold | `mobile/`: Expo/React Native scaffold (`App.tsx`, app manifest, TypeScript config, and package manifest). It has no lockfile and no test, typecheck, or build script. |
| Database | `database/schema.sql`, `database/seed.sql`, inspection query, and a role migration under `database/migrations/`. |
| Alembic | `backend/alembic/`, including environment/configuration and 40 revision files (including the merge revision). |
| Deployment | Root Compose files; backend/frontend Dockerfiles; `deployment/nginx/`; systemd units/timers; production-hardening and backup tooling. |
| Backup / restore | Deployment backup, retention, upload, health-check, restore, and restore-test shell scripts; backend backup status schema/service; operational runbooks. Separate database import/export/migrate/rollback scripts live under `scripts/database/`. |
| Tests | Backend: 17 Python test modules plus a fixture (withheld from path list). Frontend: 8 Vitest test modules. Repository/UAT scripts and test Compose configuration are present. |
| Documentation | Root README/TODO and feature README; `docs/`, `docs/audit/`, `AUDIT/`, `database/README.md`, deployment template/runbook documentation, and mobile README. |
| CI/CD | `.gitlab-ci.yml` is the only tracked CI definition. No tracked `.github/` workflow was found. |

## Validation results

| Check | Command | Result |
| --- | --- | --- |
| Python syntax | `PYTHONPYCACHEPREFIX=/private/tmp/rainbow-fashions-pycache python3 -m compileall -q backend/app` | **PASS** (exit 0). The first default-cache attempt was blocked by macOS cache permissions; rerun with an isolated temporary cache passed. |
| Backend dependencies | temporary venv + `pip install -r backend/requirements.txt` | **PASS** after an approved network retry; dependencies were installed outside the repository. |
| Backend tests | `python -m pytest` in `backend/` | **PASS** — 148 passed, 1 deprecation warning, 12.82 s. |
| Alembic head | `alembic heads` | **PASS** — `20260803_0037 (head)`. |
| Alembic history | `alembic history` | **PASS** — one merged lineage culminating in `20260803_0037`. |
| Alembic current | `alembic current` | **BLOCKED** (exit 1) — local PostgreSQL at `localhost:5432` was unavailable/blocked; no database was changed. |
| Frontend dependencies | `npm ci` in `frontend/` | **PASS** — 297 packages added. |
| Frontend tests | `npm test` | **PASS** — 8 files and 45 tests passed. |
| Frontend lint | `npm run lint` | **PASS** — ESLint completed with `--max-warnings 0`. |
| Frontend typecheck | `npm run typecheck` | **PASS** — `tsc --noEmit`. |
| Frontend build | `npm run build` | **PASS** — production build completed. Vite warned that the 615.60 kB JavaScript bundle exceeds the 500 kB chunk warning threshold. |
| Default Compose | `docker compose config` | **BLOCKED** (exit 1) — the clean worktree lacks the required local backend environment file. |
| Test Compose | `docker compose -f docker-compose.test.yml config` | **BLOCKED** (exit 1) — required `TEST_DOCKER_ENV_FILE` is not set; the command directs use of `scripts/start-test-environment.sh`. |
| Git inventory | `git ls-files`, tree/object inspection, and tracked-content pattern searches | **PASS** — 376 paths enumerated; results summarized below. |

## Alembic assessment

- Declared migration head: **`20260803_0037`**.
- The history contains a deliberate branch/merge sequence around the 20260728 revisions, then converges to a single current head.
- The repository-level migration graph is inspectable without a database. The deployed database revision could not be verified because the local database service was unreachable.

## Security and sensitive-artifact findings

All values were redacted and no environment-file content, credential, connection string, or dump was copied into this report.

1. **High risk — tracked non-example environment configuration.** Six tracked environment files were identified, including at least one non-example file. Pattern scans found database-connection and JWT/secret configuration identifiers in environment/Compose/CI/deployment-related files. Treat the non-example configuration as potentially exposed until the Git history is reviewed and all affected secrets are rotated.
2. **High risk — tracked database dumps.** Two tracked database-dump artifacts were detected. Their names and contents are intentionally withheld. They must be removed through an approved, history-aware remediation plan and any exposed credentials/data must be assessed before production.
3. **Credential/default-password indicators.** Password/default-credential/hash-related identifiers appear in test configuration, seed/migration/schema material, authentication/security modules, and documentation. The scan was filename-only to avoid exposure; verify that production paths do not retain defaults and that test-only values cannot be loaded in production.
4. **JWT/secret indicators.** JWT/secret-key identifiers occur in configuration, CI, deployment hardening, and environment-template areas. No values are reported. Confirm secrets are injected by the deployment platform and are not versioned.
5. **Private keys.** No PEM private-key header was confirmed by this assessment. The broader identifier scan found key-related configuration fields, so secret-management review is still required.
6. **Local absolute paths.** Local absolute-path patterns were found in `BARCODE_FEATURE_README.md`, `apply_barcode_feature.py`, and `docs/database-migration.md`. Replace them with repository-relative instructions before cross-machine use.
7. **Runtime uploads.** Two tracked empty runtime-upload directory placeholders were found. No uploaded content is tracked in the reviewed tree; preserve the directories or create them reliably during deployment.
8. **Generated/runtime artifacts.** Two database dumps are tracked (withheld), as is a service-worker file. Treat dump files as sensitive artifacts; verify the service worker is source-controlled intentionally rather than build output.

## Cleanup candidates — review before any deletion

### Suspected unused files

- `frontend/src/pages/BrandsPage.tsx`, `frontend/src/pages/DashboardPage.tsx`, and `frontend/src/pages/SalesPage.tsx` are not imported by `frontend/src/App.tsx` and the tracked source search found only self-references. They are candidates for route/feature review, not deletion without product confirmation.
- `apply_barcode_feature.py` is a one-off feature-application script and contains a local absolute-path reference. Confirm whether its work is already represented in history before retiring it.
- The mobile directory is a minimal Expo scaffold. It has no lockfile or CI/test/build coverage, so determine whether mobile delivery is in scope before maintaining it.

### Suspected duplicate files

- Twelve empty Python/package-marker/upload-placeholder files share the same empty blob. Most are expected structural markers and are **not** automatic deletion candidates.
- `AUDIT/android.md`, `AUDIT/database.md`, `AUDIT/deployment.md`, `AUDIT/security.md`, and `TODO.md` are all empty and share the same blob. They are documentation placeholders and should be populated, consolidated, or removed only after an owner confirms the intended audit documentation structure.

### Suspected stale documentation

- The empty `AUDIT/` placeholders and empty `TODO.md` provide no actionable current state.
- Audit material exists in both `AUDIT/` and `docs/audit/`; consolidate ownership and establish one canonical audit location.
- The barcode feature README includes machine-specific paths. The deployment and migration documents also need an environment-specific verification pass before being treated as production runbooks.
- No document was labelled stale solely by file date; these are content/ownership findings.

## Risks to resolve before production

1. Remove sensitive database dumps from the repository and assess/rotate any data or credentials they could expose.
2. Remove the tracked non-example environment configuration from version control, replace it with safe templates, and rotate all potentially exposed secrets.
3. Make production Compose validation reproducible through a documented, secret-safe environment-injection mechanism; do not commit the missing file to solve the check.
4. Verify the live database is reachable through the approved operational path and confirm its Alembic revision before deployment.
5. Resolve the frontend bundle-size warning if initial-load performance is a production requirement.
6. Establish CI coverage for the mobile scaffold or explicitly retire/de-scope it.
7. Review all destructive database scripts, especially production-data clearing/import/rollback operations, with backup and access controls before execution.

## Files and categories that must not be deleted during cleanup

- All Alembic revisions and `backend/alembic/env.py` until a migration-retention policy and a tested replacement path exist.
- Backend models, database session/base, migration metadata, and database schema/seed/migration files until database compatibility is proven.
- Deployment Nginx configuration, production-hardening scripts, backup/restore scripts, systemd units/timers, and backup/recovery runbooks until an operational owner validates replacements.
- `.gitlab-ci.yml`, root Compose files, Dockerfiles, and frontend package lockfile until CI/CD and reproducible builds are verified.
- Test modules, test orchestration scripts, and the invoice fixture until equivalent test coverage is retained.
- Runtime-upload directory placeholders (paths withheld) until deployment creates the directories safely.
- Environment files and database dumps must **not** be casually deleted or exposed; handle them through a separate, approved secret/data-remediation task with history review and rotation.

## Recommended execution order for subsequent cleanup

1. Create a security-remediation plan for tracked environment configuration and database dumps: ownership, repository-history review, data classification, secret rotation, and safe removal.
2. Make validation reproducible with documented local/test environment setup that never commits real secrets; rerun Compose and Alembic-current checks against an approved disposable environment.
3. Consolidate database migration strategy: confirm deployed revision, protect the lineage, and decide how legacy SQL migration/seed artifacts relate to Alembic.
4. Review destructive database and backup scripts with an operator; retain and test restore paths before any script consolidation.
5. Audit frontend route ownership and product requirements for the three unreferenced page modules; delete only after coverage and routing decisions are recorded.
6. Consolidate empty/duplicate audit and TODO documentation into one maintained location; remove obsolete one-off scripts only after history/function confirmation.
7. Decide whether the mobile scaffold is a supported product surface; add lockfile/CI coverage or formally remove it in a dedicated change.
8. Address frontend bundle splitting/performance after functional and security cleanup has stabilized.
