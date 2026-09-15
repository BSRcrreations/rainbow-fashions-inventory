# Changed files and purpose

All changes relative to base 1eb44105c6ef52e339acfe5195990e08fdb479ef. Includes preserved user authentication edits. 125 changed/new source files are individually hashed in SOURCE-MANIFEST.json. Evidence is not application source.

| File | Purpose |
|---|---|
| [.gitlab-ci.yml](../../.gitlab-ci.yml) | Require real PostgreSQL integration/concurrency, dependency audit, fixed installation tools and deployment gates. |
| [backend/Dockerfile](../../backend/Dockerfile) | Container runtime includes Tesseract/Poppler and fixed pip/setuptools versions. |
| [backend/alembic/sql/20260715_legacy_baseline.sql](../../backend/alembic/sql/20260715_legacy_baseline.sql) | Frozen pre-Alembic schema, enabling empty-database replay without stock/demo seeds. |
| [backend/alembic/versions/20260715_0000_legacy_baseline.py](../../backend/alembic/versions/20260715_0000_legacy_baseline.py) | Migration chain/baseline or additive roles, retail evidence, daily-stock, receipt tax and variant-threshold schema; revision purpose documented in certification. |
| [backend/alembic/versions/20260716_0001_add_product_image_url.py](../../backend/alembic/versions/20260716_0001_add_product_image_url.py) | Migration chain/baseline or additive roles, retail evidence, daily-stock, receipt tax and variant-threshold schema; revision purpose documented in certification. |
| [backend/alembic/versions/20260728_0013_purchase_item_classification_and_tenancy.py](../../backend/alembic/versions/20260728_0013_purchase_item_classification_and_tenancy.py) | Migration chain/baseline or additive roles, retail evidence, daily-stock, receipt tax and variant-threshold schema; revision purpose documented in certification. |
| [backend/alembic/versions/20260729_0030_seed_leggings_opening_stock.py](../../backend/alembic/versions/20260729_0030_seed_leggings_opening_stock.py) | Migration chain/baseline or additive roles, retail evidence, daily-stock, receipt tax and variant-threshold schema; revision purpose documented in certification. |
| [backend/alembic/versions/20260909_0049_shop_operations.py](../../backend/alembic/versions/20260909_0049_shop_operations.py) | Migration chain/baseline or additive roles, retail evidence, daily-stock, receipt tax and variant-threshold schema; revision purpose documented in certification. |
| [backend/alembic/versions/20260909_0050_retail_transactions.py](../../backend/alembic/versions/20260909_0050_retail_transactions.py) | Migration chain/baseline or additive roles, retail evidence, daily-stock, receipt tax and variant-threshold schema; revision purpose documented in certification. |
| [backend/alembic/versions/20260909_0051_daily_stock.py](../../backend/alembic/versions/20260909_0051_daily_stock.py) | Migration chain/baseline or additive roles, retail evidence, daily-stock, receipt tax and variant-threshold schema; revision purpose documented in certification. |
| [backend/alembic/versions/20260910_0052_receipt_tax_snapshots.py](../../backend/alembic/versions/20260910_0052_receipt_tax_snapshots.py) | Migration chain/baseline or additive roles, retail evidence, daily-stock, receipt tax and variant-threshold schema; revision purpose documented in certification. |
| [backend/alembic/versions/20260910_0053_variant_minimum_stock.py](../../backend/alembic/versions/20260910_0053_variant_minimum_stock.py) | Migration chain/baseline or additive roles, retail evidence, daily-stock, receipt tax and variant-threshold schema; revision purpose documented in certification. |
| [backend/app/ai/local_ocr.py](../../backend/app/ai/local_ocr.py) | Local image/HEIC/native-text/scanned-page PDF extraction with bounded subprocesses and cleanup. |
| [backend/app/api/deps.py](../../backend/app/api/deps.py) | Server-side role and store authorization dependencies. |
| [backend/app/api/routes/customers.py](../../backend/app/api/routes/customers.py) | Enforce role/store boundaries and expose the corresponding inventory, transaction, report or operational workflow. |
| [backend/app/api/routes/dashboard.py](../../backend/app/api/routes/dashboard.py) | Enforce role/store boundaries and expose the corresponding inventory, transaction, report or operational workflow. |
| [backend/app/api/routes/expenses.py](../../backend/app/api/routes/expenses.py) | Enforce role/store boundaries and expose the corresponding inventory, transaction, report or operational workflow. |
| [backend/app/api/routes/opening_stock_imports.py](../../backend/app/api/routes/opening_stock_imports.py) | Enforce role/store boundaries and expose the corresponding inventory, transaction, report or operational workflow. |
| [backend/app/api/routes/operations.py](../../backend/app/api/routes/operations.py) | Enforce role/store boundaries and expose the corresponding inventory, transaction, report or operational workflow. |
| [backend/app/api/routes/products.py](../../backend/app/api/routes/products.py) | Enforce role/store boundaries and expose the corresponding inventory, transaction, report or operational workflow. |
| [backend/app/api/routes/purchase_documents.py](../../backend/app/api/routes/purchase_documents.py) | Enforce role/store boundaries and expose the corresponding inventory, transaction, report or operational workflow. |
| [backend/app/api/routes/purchases.py](../../backend/app/api/routes/purchases.py) | Enforce role/store boundaries and expose the corresponding inventory, transaction, report or operational workflow. |
| [backend/app/api/routes/reports.py](../../backend/app/api/routes/reports.py) | Enforce role/store boundaries and expose the corresponding inventory, transaction, report or operational workflow. |
| [backend/app/api/routes/sales.py](../../backend/app/api/routes/sales.py) | Enforce role/store boundaries and expose the corresponding inventory, transaction, report or operational workflow. |
| [backend/app/api/routes/stock.py](../../backend/app/api/routes/stock.py) | Enforce role/store boundaries and expose the corresponding inventory, transaction, report or operational workflow. |
| [backend/app/api/routes/stock_scan.py](../../backend/app/api/routes/stock_scan.py) | Enforce role/store boundaries and expose the corresponding inventory, transaction, report or operational workflow. |
| [backend/app/api/routes/suppliers.py](../../backend/app/api/routes/suppliers.py) | Enforce role/store boundaries and expose the corresponding inventory, transaction, report or operational workflow. |
| [backend/app/core/security.py](../../backend/app/core/security.py) | Use tested PyJWT token handling with secure verification configuration. |
| [backend/app/main.py](../../backend/app/main.py) | Register operational routes/providers and lazy-load application screens. |
| [backend/app/models/__init__.py](../../backend/app/models/__init__.py) | Persist transaction, store operation, tax snapshot, role or variant threshold evidence. |
| [backend/app/models/enums.py](../../backend/app/models/enums.py) | Persist transaction, store operation, tax snapshot, role or variant threshold evidence. |
| [backend/app/models/operations.py](../../backend/app/models/operations.py) | Persist transaction, store operation, tax snapshot, role or variant threshold evidence. |
| [backend/app/models/product_variant.py](../../backend/app/models/product_variant.py) | Persist transaction, store operation, tax snapshot, role or variant threshold evidence. |
| [backend/app/models/purchase.py](../../backend/app/models/purchase.py) | Persist transaction, store operation, tax snapshot, role or variant threshold evidence. |
| [backend/app/models/purchase_return.py](../../backend/app/models/purchase_return.py) | Persist transaction, store operation, tax snapshot, role or variant threshold evidence. |
| [backend/app/models/sale.py](../../backend/app/models/sale.py) | Persist transaction, store operation, tax snapshot, role or variant threshold evidence. |
| [backend/app/repositories/product.py](../../backend/app/repositories/product.py) | Scope records and load/lock the required product, purchase or sale state consistently. |
| [backend/app/repositories/purchase.py](../../backend/app/repositories/purchase.py) | Scope records and load/lock the required product, purchase or sale state consistently. |
| [backend/app/repositories/sale.py](../../backend/app/repositories/sale.py) | Scope records and load/lock the required product, purchase or sale state consistently. |
| [backend/app/schemas/backup.py](../../backend/app/schemas/backup.py) | Validate and serialize exact-size transaction, draft, report and operational API contracts. |
| [backend/app/schemas/inventory_reconciliation.py](../../backend/app/schemas/inventory_reconciliation.py) | Validate and serialize exact-size transaction, draft, report and operational API contracts. |
| [backend/app/schemas/operations.py](../../backend/app/schemas/operations.py) | Validate and serialize exact-size transaction, draft, report and operational API contracts. |
| [backend/app/schemas/product.py](../../backend/app/schemas/product.py) | Validate and serialize exact-size transaction, draft, report and operational API contracts. |
| [backend/app/schemas/purchase.py](../../backend/app/schemas/purchase.py) | Validate and serialize exact-size transaction, draft, report and operational API contracts. |
| [backend/app/schemas/sale.py](../../backend/app/schemas/sale.py) | Validate and serialize exact-size transaction, draft, report and operational API contracts. |
| [backend/app/schemas/stock.py](../../backend/app/schemas/stock.py) | Validate and serialize exact-size transaction, draft, report and operational API contracts. |
| [backend/app/schemas/stock_scan.py](../../backend/app/schemas/stock_scan.py) | Validate and serialize exact-size transaction, draft, report and operational API contracts. |
| [backend/app/services/auth_service.py](../../backend/app/services/auth_service.py) | Preserved existing user change: normalize login email handling. |
| [backend/app/services/backup_status_service.py](../../backend/app/services/backup_status_service.py) | Implement backup status behavior with store scoping, validated transactions and auditable state. |
| [backend/app/services/business_service.py](../../backend/app/services/business_service.py) | Implement business behavior with store scoping, validated transactions and auditable state. |
| [backend/app/services/dashboard_service.py](../../backend/app/services/dashboard_service.py) | Implement dashboard behavior with store scoping, validated transactions and auditable state. |
| [backend/app/services/inventory_reconciliation_service.py](../../backend/app/services/inventory_reconciliation_service.py) | Implement inventory reconciliation behavior with store scoping, validated transactions and auditable state. |
| [backend/app/services/opening_stock_import_service.py](../../backend/app/services/opening_stock_import_service.py) | Implement opening stock import behavior with store scoping, validated transactions and auditable state. |
| [backend/app/services/operations_service.py](../../backend/app/services/operations_service.py) | Implement operations behavior with store scoping, validated transactions and auditable state. |
| [backend/app/services/product_service.py](../../backend/app/services/product_service.py) | Implement product behavior with store scoping, validated transactions and auditable state. |
| [backend/app/services/purchase_document_service.py](../../backend/app/services/purchase_document_service.py) | Implement purchase document behavior with store scoping, validated transactions and auditable state. |
| [backend/app/services/purchase_service.py](../../backend/app/services/purchase_service.py) | Implement purchase behavior with store scoping, validated transactions and auditable state. |
| [backend/app/services/report_export_service.py](../../backend/app/services/report_export_service.py) | Implement report export behavior with store scoping, validated transactions and auditable state. |
| [backend/app/services/report_service.py](../../backend/app/services/report_service.py) | Implement report behavior with store scoping, validated transactions and auditable state. |
| [backend/app/services/sale_discount.py](../../backend/app/services/sale_discount.py) | Implement sale discount behavior with store scoping, validated transactions and auditable state. |
| [backend/app/services/sale_service.py](../../backend/app/services/sale_service.py) | Implement sale behavior with store scoping, validated transactions and auditable state. |
| [backend/app/services/shop_summary_service.py](../../backend/app/services/shop_summary_service.py) | Implement shop summary behavior with store scoping, validated transactions and auditable state. |
| [backend/app/services/stock_scan_service.py](../../backend/app/services/stock_scan_service.py) | Implement stock scan behavior with store scoping, validated transactions and auditable state. |
| [backend/app/services/stock_service.py](../../backend/app/services/stock_service.py) | Implement stock behavior with store scoping, validated transactions and auditable state. |
| [backend/app/services/transaction_idempotency.py](../../backend/app/services/transaction_idempotency.py) | Implement transaction idempotency behavior with store scoping, validated transactions and auditable state. |
| [backend/app/services/variant_management_service.py](../../backend/app/services/variant_management_service.py) | Implement variant management behavior with store scoping, validated transactions and auditable state. |
| [backend/requirements.txt](../../backend/requirements.txt) | Pin compatible backend dependencies and replace vulnerable packages; audited with zero known vulnerabilities. |
| [backend/scripts/bootstrap_test_database.py](../../backend/scripts/bootstrap_test_database.py) | Bootstrap disposable TEST data through the real Alembic chain. |
| [backend/scripts/verify_retail_concurrency.py](../../backend/scripts/verify_retail_concurrency.py) | Execute disposable PostgreSQL races for final-piece sales and repeated sale/stock confirmation. |
| [backend/tests/conftest.py](../../backend/tests/conftest.py) | Permanent regression coverage for the corresponding stock, purchase, sale, security, reporting or browser behavior. |
| [backend/tests/test_batch_barcodes.py](../../backend/tests/test_batch_barcodes.py) | Permanent regression coverage for the corresponding stock, purchase, sale, security, reporting or browser behavior. |
| [backend/tests/test_existing_variant_barcode_onboarding.py](../../backend/tests/test_existing_variant_barcode_onboarding.py) | Permanent regression coverage for the corresponding stock, purchase, sale, security, reporting or browser behavior. |
| [backend/tests/test_local_ocr.py](../../backend/tests/test_local_ocr.py) | Permanent regression coverage for the corresponding stock, purchase, sale, security, reporting or browser behavior. |
| [backend/tests/test_master_retail_workflows.py](../../backend/tests/test_master_retail_workflows.py) | Permanent regression coverage for the corresponding stock, purchase, sale, security, reporting or browser behavior. |
| [backend/tests/test_password_security.py](../../backend/tests/test_password_security.py) | Preserved existing user authentication/password regression changes; included in the final suite. |
| [backend/tests/test_reports.py](../../backend/tests/test_reports.py) | Permanent regression coverage for the corresponding stock, purchase, sale, security, reporting or browser behavior. |
| [backend/tests/test_stage1_validation.py](../../backend/tests/test_stage1_validation.py) | Permanent regression coverage for the corresponding stock, purchase, sale, security, reporting or browser behavior. |
| [deployment/scripts/deploy_release.sh](../../deployment/scripts/deploy_release.sh) | Replay migrations for empty or versioned deployments; reject unknown baselines and preserve rollback safeguards. |
| [docs/master-spec/CERTIFICATION-MATRIX.md](../../docs/master-spec/CERTIFICATION-MATRIX.md) | Certification report, requirement/file index, source fingerprints, operator/pilot/release guidance or import template. |
| [docs/master-spec/CHANGED-FILES.md](../../docs/master-spec/CHANGED-FILES.md) | Certification report, requirement/file index, source fingerprints, operator/pilot/release guidance or import template. |
| [docs/master-spec/FINAL-CERTIFICATION.md](../../docs/master-spec/FINAL-CERTIFICATION.md) | Certification report, requirement/file index, source fingerprints, operator/pilot/release guidance or import template. |
| [docs/master-spec/GO-LIVE-CHECKS.md](../../docs/master-spec/GO-LIVE-CHECKS.md) | Certification report, requirement/file index, source fingerprints, operator/pilot/release guidance or import template. |
| [docs/master-spec/MODIFIED-FILES.txt](../../docs/master-spec/MODIFIED-FILES.txt) | Certification report, requirement/file index, source fingerprints, operator/pilot/release guidance or import template. |
| [docs/master-spec/OPERATOR-GUIDE.md](../../docs/master-spec/OPERATOR-GUIDE.md) | Certification report, requirement/file index, source fingerprints, operator/pilot/release guidance or import template. |
| [docs/master-spec/READINESS.md](../../docs/master-spec/READINESS.md) | Certification report, requirement/file index, source fingerprints, operator/pilot/release guidance or import template. |
| [docs/master-spec/RELEASE-CHECKLIST.md](../../docs/master-spec/RELEASE-CHECKLIST.md) | Certification report, requirement/file index, source fingerprints, operator/pilot/release guidance or import template. |
| [docs/master-spec/SOURCE-MANIFEST.json](../../docs/master-spec/SOURCE-MANIFEST.json) | Certification report, requirement/file index, source fingerprints, operator/pilot/release guidance or import template. |
| [docs/master-spec/evidence/backup-restore.json](../../docs/master-spec/evidence/backup-restore.json) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/concurrency.json](../../docs/master-spec/evidence/concurrency.json) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-backend.txt](../../docs/master-spec/evidence/final-backend.txt) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-browser-final.txt](../../docs/master-spec/evidence/final-browser-final.txt) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-build.txt](../../docs/master-spec/evidence/final-build.txt) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-capacity.txt](../../docs/master-spec/evidence/final-capacity.txt) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-chromium-phone.png](../../docs/master-spec/evidence/final-chromium-phone.png) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-chromium-tablet.png](../../docs/master-spec/evidence/final-chromium-tablet.png) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-concurrency.json](../../docs/master-spec/evidence/final-concurrency.json) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-container-audit.json](../../docs/master-spec/evidence/final-container-audit.json) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-container-audit.txt](../../docs/master-spec/evidence/final-container-audit.txt) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-deployment.json](../../docs/master-spec/evidence/final-deployment.json) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-docker.txt](../../docs/master-spec/evidence/final-docker.txt) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-extra-browser.txt](../../docs/master-spec/evidence/final-extra-browser.txt) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-final-layout.txt](../../docs/master-spec/evidence/final-final-layout.txt) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-frontend.txt](../../docs/master-spec/evidence/final-frontend.txt) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-history-secrets.json](../../docs/master-spec/evidence/final-history-secrets.json) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-history-secrets.txt](../../docs/master-spec/evidence/final-history-secrets.txt) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-lint.txt](../../docs/master-spec/evidence/final-lint.txt) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-migrations.txt](../../docs/master-spec/evidence/final-migrations.txt) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-npm-audit.json](../../docs/master-spec/evidence/final-npm-audit.json) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-ocr.txt](../../docs/master-spec/evidence/final-ocr.txt) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-pip-audit.json](../../docs/master-spec/evidence/final-pip-audit.json) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-pip-audit.txt](../../docs/master-spec/evidence/final-pip-audit.txt) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-production-build.txt](../../docs/master-spec/evidence/final-production-build.txt) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-restore.json](../../docs/master-spec/evidence/final-restore.json) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-restore.txt](../../docs/master-spec/evidence/final-restore.txt) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-secrets.json](../../docs/master-spec/evidence/final-secrets.json) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-secrets.txt](../../docs/master-spec/evidence/final-secrets.txt) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-security-policy.txt](../../docs/master-spec/evidence/final-security-policy.txt) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-typecheck.txt](../../docs/master-spec/evidence/final-typecheck.txt) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-upgrade.txt](../../docs/master-spec/evidence/final-upgrade.txt) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-webkit-phone.png](../../docs/master-spec/evidence/final-webkit-phone.png) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/final-webkit-tablet.png](../../docs/master-spec/evidence/final-webkit-tablet.png) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/npm-audit.json](../../docs/master-spec/evidence/npm-audit.json) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/pip-audit.json](../../docs/master-spec/evidence/pip-audit.json) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/quick-stock-phone.png](../../docs/master-spec/evidence/quick-stock-phone.png) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/quick-stock-tablet.png](../../docs/master-spec/evidence/quick-stock-tablet.png) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/receipt-desktop.png](../../docs/master-spec/evidence/receipt-desktop.png) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/reports-desktop.png](../../docs/master-spec/evidence/reports-desktop.png) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/evidence/workingtree-secret-scan.json](../../docs/master-spec/evidence/workingtree-secret-scan.json) | Recorded verification evidence; final- files are current certification, other files retain historical scope. |
| [docs/master-spec/opening-stock-template.csv](../../docs/master-spec/opening-stock-template.csv) | Certification report, requirement/file index, source fingerprints, operator/pilot/release guidance or import template. |
| [frontend/Dockerfile](../../frontend/Dockerfile) | Build the tested frontend using Node 22. |
| [frontend/package-lock.json](../../frontend/package-lock.json) | Tested frontend dependency/lock updates, security fixes and fake IndexedDB regression support. |
| [frontend/package.json](../../frontend/package.json) | Tested frontend dependency/lock updates, security fixes and fake IndexedDB regression support. |
| [frontend/src/App.tsx](../../frontend/src/App.tsx) | Register operational routes/providers and lazy-load application screens. |
| [frontend/src/api/client.ts](../../frontend/src/api/client.ts) | Support idempotency headers for atomic draft PUT requests. |
| [frontend/src/components/BarcodeLabelDialog.tsx](../../frontend/src/components/BarcodeLabelDialog.tsx) | Reusable accessible variant selection, error/network display, configurable print or stock report interface. |
| [frontend/src/components/ConnectionStatus.tsx](../../frontend/src/components/ConnectionStatus.tsx) | Reusable accessible variant selection, error/network display, configurable print or stock report interface. |
| [frontend/src/components/ErrorState.tsx](../../frontend/src/components/ErrorState.tsx) | Reusable accessible variant selection, error/network display, configurable print or stock report interface. |
| [frontend/src/components/LowStockReport.tsx](../../frontend/src/components/LowStockReport.tsx) | Reusable accessible variant selection, error/network display, configurable print or stock report interface. |
| [frontend/src/components/ThermalReceipt.tsx](../../frontend/src/components/ThermalReceipt.tsx) | Reusable accessible variant selection, error/network display, configurable print or stock report interface. |
| [frontend/src/components/VariantManagementDialog.tsx](../../frontend/src/components/VariantManagementDialog.tsx) | Reusable accessible variant selection, error/network display, configurable print or stock report interface. |
| [frontend/src/components/VariantPicker.tsx](../../frontend/src/components/VariantPicker.tsx) | Reusable accessible variant selection, error/network display, configurable print or stock report interface. |
| [frontend/src/hooks/useAuth.test.tsx](../../frontend/src/hooks/useAuth.test.tsx) | Permanent regression coverage for the corresponding stock, purchase, sale, security, reporting or browser behavior. |
| [frontend/src/hooks/useAuth.tsx](../../frontend/src/hooks/useAuth.tsx) | Recover account-scoped drafts/attachments or settings; preserve valid authentication during network interruption. |
| [frontend/src/hooks/useDraftAttachment.ts](../../frontend/src/hooks/useDraftAttachment.ts) | Recover account-scoped drafts/attachments or settings; preserve valid authentication during network interruption. |
| [frontend/src/hooks/useDurableDraft.ts](../../frontend/src/hooks/useDurableDraft.ts) | Recover account-scoped drafts/attachments or settings; preserve valid authentication during network interruption. |
| [frontend/src/hooks/useStoreSettings.ts](../../frontend/src/hooks/useStoreSettings.ts) | Recover account-scoped drafts/attachments or settings; preserve valid authentication during network interruption. |
| [frontend/src/layouts/AppLayout.tsx](../../frontend/src/layouts/AppLayout.tsx) | Role-filtered navigation and protected application access with recovery-aware authentication. |
| [frontend/src/main.tsx](../../frontend/src/main.tsx) | Register operational routes/providers and lazy-load application screens. |
| [frontend/src/pages/AuditLogPage.tsx](../../frontend/src/pages/AuditLogPage.tsx) | Implement the AuditLog operator workflow and its validation, exact-size handling or recovery behavior. |
| [frontend/src/pages/BackupStatusPage.tsx](../../frontend/src/pages/BackupStatusPage.tsx) | Implement the BackupStatus operator workflow and its validation, exact-size handling or recovery behavior. |
| [frontend/src/pages/DayClosingPage.tsx](../../frontend/src/pages/DayClosingPage.tsx) | Implement the DayClosing operator workflow and its validation, exact-size handling or recovery behavior. |
| [frontend/src/pages/InventoryIntegrityPage.tsx](../../frontend/src/pages/InventoryIntegrityPage.tsx) | Implement the InventoryIntegrity operator workflow and its validation, exact-size handling or recovery behavior. |
| [frontend/src/pages/NewSalePage.test.tsx](../../frontend/src/pages/NewSalePage.test.tsx) | Permanent regression coverage for the corresponding stock, purchase, sale, security, reporting or browser behavior. |
| [frontend/src/pages/NewSalePage.tsx](../../frontend/src/pages/NewSalePage.tsx) | Implement the NewSale operator workflow and its validation, exact-size handling or recovery behavior. |
| [frontend/src/pages/OpeningStockImportPage.tsx](../../frontend/src/pages/OpeningStockImportPage.tsx) | Implement the OpeningStockImport operator workflow and its validation, exact-size handling or recovery behavior. |
| [frontend/src/pages/PrinterSettingsPage.tsx](../../frontend/src/pages/PrinterSettingsPage.tsx) | Implement the PrinterSettings operator workflow and its validation, exact-size handling or recovery behavior. |
| [frontend/src/pages/PurchaseDetailPage.tsx](../../frontend/src/pages/PurchaseDetailPage.tsx) | Implement the PurchaseDetail operator workflow and its validation, exact-size handling or recovery behavior. |
| [frontend/src/pages/PurchaseReturnsPage.tsx](../../frontend/src/pages/PurchaseReturnsPage.tsx) | Implement the PurchaseReturns operator workflow and its validation, exact-size handling or recovery behavior. |
| [frontend/src/pages/PurchasesPage.tsx](../../frontend/src/pages/PurchasesPage.tsx) | Implement the Purchases operator workflow and its validation, exact-size handling or recovery behavior. |
| [frontend/src/pages/QuickEntryPage.tsx](../../frontend/src/pages/QuickEntryPage.tsx) | Implement the QuickEntry operator workflow and its validation, exact-size handling or recovery behavior. |
| [frontend/src/pages/ReportsPage.tsx](../../frontend/src/pages/ReportsPage.tsx) | Implement the Reports operator workflow and its validation, exact-size handling or recovery behavior. |
| [frontend/src/pages/ReturnsPage.tsx](../../frontend/src/pages/ReturnsPage.tsx) | Implement the Returns operator workflow and its validation, exact-size handling or recovery behavior. |
| [frontend/src/pages/SalesDashboardPage.tsx](../../frontend/src/pages/SalesDashboardPage.tsx) | Implement the SalesDashboard operator workflow and its validation, exact-size handling or recovery behavior. |
| [frontend/src/pages/SalesHistoryPage.tsx](../../frontend/src/pages/SalesHistoryPage.tsx) | Implement the SalesHistory operator workflow and its validation, exact-size handling or recovery behavior. |
| [frontend/src/pages/StockAdjustmentPage.tsx](../../frontend/src/pages/StockAdjustmentPage.tsx) | Implement the StockAdjustment operator workflow and its validation, exact-size handling or recovery behavior. |
| [frontend/src/pages/StoreSettingsPage.tsx](../../frontend/src/pages/StoreSettingsPage.tsx) | Implement the StoreSettings operator workflow and its validation, exact-size handling or recovery behavior. |
| [frontend/src/pages/UsersPage.tsx](../../frontend/src/pages/UsersPage.tsx) | Implement the Users operator workflow and its validation, exact-size handling or recovery behavior. |
| [frontend/src/pages/certification.behavior.test.tsx](../../frontend/src/pages/certification.behavior.test.tsx) | Permanent regression coverage for the corresponding stock, purchase, sale, security, reporting or browser behavior. |
| [frontend/src/pages/newSaleLogic.ts](../../frontend/src/pages/newSaleLogic.ts) | Implement the newSaleLogic operator workflow and its validation, exact-size handling or recovery behavior. |
| [frontend/src/pages/retailWorkflows.behavior.test.tsx](../../frontend/src/pages/retailWorkflows.behavior.test.tsx) | Permanent regression coverage for the corresponding stock, purchase, sale, security, reporting or browser behavior. |
| [frontend/src/routes/ProtectedRoute.tsx](../../frontend/src/routes/ProtectedRoute.tsx) | Role-filtered navigation and protected application access with recovery-aware authentication. |
| [frontend/src/routes/permissions.ts](../../frontend/src/routes/permissions.ts) | Role-filtered navigation and protected application access with recovery-aware authentication. |
| [frontend/src/types/index.ts](../../frontend/src/types/index.ts) | Frontend types for expanded stock, purchase, sale and operational responses. |
| [frontend/src/utils/draftStorage.ts](../../frontend/src/utils/draftStorage.ts) | Reusable durable-request/draft identity, exact-variant selection or browser printing helpers. |
| [frontend/src/utils/printing.ts](../../frontend/src/utils/printing.ts) | Reusable durable-request/draft identity, exact-variant selection or browser printing helpers. |
| [frontend/src/utils/variantSelection.ts](../../frontend/src/utils/variantSelection.ts) | Reusable durable-request/draft identity, exact-variant selection or browser printing helpers. |
