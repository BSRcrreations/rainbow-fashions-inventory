# Live UI Gap Report

Audit date: 2026-08-03. Scope is the isolated local UAT application only.

## Executive Summary

The core UAT sale and scan workflows work end to end after two verified runtime
fixes: valid test-account emails and a complete `SupplierPayment` relationship.
The application is **not ready for production** because current SQLAlchemy
models require an uncommitted migration after the tracked Alembic head.

## Working End To End

- Owner login and protected navigation.
- Dashboard empty state with live inventory totals.
- Product list, six exact-size variants, product rename, and refresh
  persistence without editing stock directly.
- New Sale cart-line visibility, exact variant selection, 10% discount, sale
  completion, stock deduction, and Sales History persistence.
- Known barcode resolution, repeated-scan quantity accumulation, review, and
  confirmed immutable stock posting.

## Backend-Ready Or Frontend-Connected, But Not UAT Verified

- Category, subcategory, and brand CRUD.
- Product image lifecycle, import/export, safe deletion, and barcode printing.
- Stock adjustment, correction, reset, export, and owner controls.
- Purchase upload, OCR polling, review, confirmation, cancellation, and void.
- Sale editing, returns, voiding, exports, and role-specific denial paths.
- Backup scheduler, offsite backup, restore drill, retention, and monitoring.

## Production Blockers

| Severity | Finding | Impact | Required action |
| --- | --- | --- | --- |
| BLOCKER | `20260803_0037_business_accounts_expenses_reports.py` is untracked while models use `sales.customer_id` and related tables. | A database at the tracked head (`0036`) raises a runtime `UndefinedColumn` error on the dashboard. | Review and commit the migration with its models/routes/tests, rebuild, migrate a disposable database, then re-run UAT. |
| BLOCKER | The UAT bootstrap uses `Base.metadata.create_all()` and stamps Alembic head. | It can make a test DB appear migrated even when a migration is absent from the image. | Make the migration chain authoritative for a fresh-test bootstrap or ensure the committed baseline schema matches head. |
| BLOCKER | Backup/restore is documented but no scheduler, restore drill, or failure visibility was browser-verified. | Data-recovery claims are not operationally proven. | Run an isolated restore exercise and document evidence before production approval. |

## High-Severity Gaps

| Finding | Why it matters | Recommended order |
| --- | --- | --- |
| Store isolation and role denial lack two-store browser/API UAT. | Cross-tenant or privilege regressions would be severe. | 1 |
| Stock reset, correction, sale void, return, and purchase confirmation are only automated-tested. | These mutate financial or inventory history. | 2 |
| Purchase OCR intake is not browser-tested with an uploaded document. | A key receiving workflow remains unproven. | 3 |
| Product image, import/export, safe deletion, and barcode transfer lack browser coverage. | Operational catalog workflows could fail in daily use. | 4 |

## Medium And Low Gaps

- The Products page briefly displays `0 products` before its query resolves;
  it resolves to the correct two products. This is a loading-state usability
  issue, not a data mismatch.
- Only the Codex in-app browser was available. Safari and Chromium browser
  verification were not available in this audit session.
- The production bundle is 594 KB minified and Vite emits a code-splitting
  warning. This is a performance follow-up, not a build failure.
- The Docker backend image does not include tests by default. A plain container
  `pytest` did not exercise repository tests; the authoritative audit run
  mounted `backend/tests` read-only and passed 148 tests.

## Recommended Implementation Order

1. Commit and validate migration `0037` with the business-account model set.
2. Replace schema stamping as the only new-test bootstrap evidence with a
   migration-chain validation job.
3. Add API/browser UAT for cross-store denial and destructive inventory/sale
   operations.
4. Exercise purchase OCR and data-protection restore using non-production
   fixtures.
5. Add code splitting for the largest frontend route bundle.
