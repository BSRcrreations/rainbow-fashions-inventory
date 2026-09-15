# Rainbow Fashions final completion and go-live certification

15 September 2026 · **NO-GO for real opening inventory**

The local implementation and verification work is complete. Final source suites, builds, scans, migrations, browser workflows and restore evidence were refreshed on 15 September; the unchanged opening-import capacity and scanned-PDF OCR evidence retain their 13 September scope. The working application passed the software checks below, including real PostgreSQL transactions and both browser engines. Production certification remains incomplete because external recovery, release and shop-device checks are not available. No production database, products or stock were changed.

Candidate: uncommitted working tree on `shop-inventory`, base `1eb44105c6ef52e339acfe5195990e08fdb479ef`. The base commit does **not** contain these changes. [SOURCE-MANIFEST.json](SOURCE-MANIFEST.json) identifies changed source files by SHA-256. Existing user changes in authentication and password tests were preserved. This report supersedes earlier readiness summaries; only `final-*` evidence describes this certification round unless explicitly stated otherwise.

## 1. Master requirement matrix

[CERTIFICATION-MATRIX.md](CERTIFICATION-MATRIX.md) covers all **55 original sections**, with COMPLETE, PARTIAL or EXTERNAL VERIFICATION REQUIRED status and before/after evidence. COMPLETE means the software requirement is implemented and locally verified within the documented scope. It does not certify physical devices or the production host. [GO-LIVE-CHECKS.md](GO-LIVE-CHECKS.md) separately enumerates every acceptance check from original section 51. Performance under real server load remains PARTIAL; hardware, accessibility/staff acceptance, offsite recovery and remote deployment remain external.

## 2. Changes made

[CHANGED-FILES.md](CHANGED-FILES.md) lists every changed/new file and its purpose; [MODIFIED-FILES.txt](MODIFIED-FILES.txt) provides the path inventory.

The implementation adds exact-size stock and purchase drafts, stable retry identities, atomic purchase saves, supplier returns, atomic cash/credit exchanges, discounted/damaged returns, configurable receipt/label printing, day closing, roles, audit, backup status, report exports and size-level stock thresholds. Reconciliation compares movements, variants, aggregate totals and cost evidence.

This final round fixed defects discovered through integration testing: multi-size consistency, product-only adjustment ambiguity, zero-count correction, missing invoice settings/store arguments, OCR review lines not becoming actual purchase items, interrupted authentication requests logging out a valid user, and WebKit losing selected photo handles after reload. Photo drafts now store bytes. The global New Sale action sits in the header, so it no longer overlays phone size controls. Docker/CI require fixed pip and setuptools versions; local build tools were refreshed after the audit identified advisories. Formal purchase edits and line replacement save as one versioned transaction. Scanned PDF pages use Poppler/Tesseract; HEIC photos are converted locally before OCR. OCR never confirms inventory.

## 3. Database migrations

| Check | Result |
|---|---|
| Previous head | `20260904_0048` |
| Current head | `20260910_0053`, exactly one head |
| Empty PostgreSQL → full Alembic chain | PASS; stores, products, variants and stock history all remain empty |
| Existing synthetic schema/data at 0048 → 0053 | PASS; synthetic store retained, no unsolicited products |
| Actual production-backup rehearsal | EXTERNAL VERIFICATION REQUIRED |

New revisions: `20260715_0000` frozen empty legacy schema baseline; `20260909_0049` roles/settings/audit/closing; `0050` retail purchase/return/exchange fields; `0051` daily-stock mode; `20260910_0052` recorded receipt tax data; `0053` optional variant minimum stock. Revision 0001 links to the baseline; the existing 0013 empty-store guard and retired 0030 automatic seed were corrected for fresh installs. Previously applied real business data is retained. Nonempty unversioned databases are rejected instead of guessed/stamped. Evidence-bearing downgrades refuse destructive deletion.

[Migration evidence](evidence/final-migrations.txt). Migration file hashes are in the source manifest. Production was not used as a migration target.

## 4. Backend validation

**317 passed, 11 warnings, 16.68 seconds**: 297 backend tests plus 20 deployment-script tests, after the final source changes. The warnings are dependency deprecations, not failed assertions.

Executed from `backend` using the isolated Python 3.11 environment:

```bash
APP_ENV=testing \
DATABASE_URL=postgresql+psycopg://rainbow_test@127.0.0.1:55439/rainbow_master_test \
RAINBOW_TEST_DATABASE_URL=postgresql+psycopg://rainbow_test@127.0.0.1:55439/rainbow_master_test \
/Users/subbu/.cache/rainbow-certification/venv/bin/python -m pytest tests ../deployment/tests -q
```

[Full result](evidence/final-backend.txt). Real PostgreSQL coverage includes failed-write rollback, tenant and role boundaries, idempotency, insufficient stock, returns, closing, accounts, tax snapshots, import safety and invoice review. A separate concurrency run proves one winner for the final piece, one invoice for simultaneous identical sale keys, and one stock effect for concurrent draft confirmation. [Concurrency evidence](evidence/final-concurrency.json).

## 5. Frontend validation

| Executed command | Result |
|---|---|
| `npm --prefix frontend test -- --run` | 18 test files; **81 tests passed** |
| `npm --prefix frontend run lint` | PASS, ESLint with zero-warning limit |
| `npm --prefix frontend run typecheck` | PASS, `tsc --noEmit` |
| `npm --prefix frontend run build` | PASS; largest initial app chunk 230.04 kB, gzip 75.13 kB |

Evidence: [tests](evidence/final-frontend.txt), [lint](evidence/final-lint.txt), [typecheck](evidence/final-typecheck.txt), [build](evidence/final-build.txt). Regression tests exercise actual rendered draft recovery, shared-size choice, original-request retry, auth interruption and receipt reprinting without a sale mutation.

## 6. Security

Latest dependency scans returned **zero known vulnerabilities**: [pip-audit](evidence/final-pip-audit.json) and [npm audit](evidence/final-npm-audit.json). The [rebuilt backend image’s complete installed Python package list](evidence/final-container-audit.json) also returned zero known vulnerabilities. The initial refreshed scan found advisories in pip/setuptools; fixed versions are now installed and required in CI/Docker. Gitleaks working-tree and Git-history scans returned **no leaks**. Tracked-secret, fixed-password-hash and repository-artifact policies passed. [Security checks](evidence/final-security-policy.txt), [working tree](evidence/final-secrets.txt), [Git history](evidence/final-history-secrets.txt).

Password hashing, secure bootstrap/session configuration and direct API permission checks are covered by source tests. Nonowners are denied owner user/settings/reversal actions; viewer sale writes are denied. Scans do not attest the production TLS/firewall, host access, OS/container vulnerabilities or live account configuration. Credentials, browser auth state and backup dumps remain outside the repository.

## 7. Inventory integrity

The permanent regression `test_certification_exact_four_size_lifecycle_and_shared_barcode` proves the requested lifecycle:

| Action | S | M | L | XL | Product total |
|---|---:|---:|---:|---:|---:|
| Opening stock | 10 | 15 | 20 | 12 | **57** |
| Sell M × 2 | 10 | 13 | 20 | 12 | **55** |
| Sellable return M × 1 | 10 | 14 | 20 | 12 | **56** |
| Adjust XL −2 | 10 | 14 | 20 | 10 | **54** |
| Purchase L × 5 | 10 | 14 | 25 | 10 | **59** |

Every stage checks exact variants, product totals and store inventory totals. Final movement-derived reconciliation has **zero unexplained discrepancies** for the fixture. Later activity blocks reversal of the opening import. This is a synthetic database proof, not a claim about the uninspected real shop inventory.

## 8. Shared barcode

A six-size S/M/L/XL/2XL/3XL chooser requires a conscious selection; no automatic allocation is permitted. Frontend tests prove the callback is not called before selection. Database ambiguous lookup returns a rejection. Browser runs selected exact sizes through Quick Stock Entry, Quick Purchase, formal purchase and barcode billing. Stock adjustment uses the same exact-variant picker. Opening import represents each size in its own SKU/size row and requires explicit shared-family approval; it does not guess from the barcode.

## 9. Sales

Both Chromium and WebKit completed category-based cash sales, typed-barcode shared-size sales and text-search sales. Exact stock effects were checked in the full workflow. Server tests verify Cash, UPI, Card, Bank and other supported modes, required references, credit limits and combined discount limits. Category/search workflows function without a scanner. Physical scanning remains external.

[Full browser flows](evidence/final-browser-final.txt), [barcode/search and layout checks](evidence/final-extra-browser.txt).

## 10. Stock entry

Quick Stock Entry supports barcode, category and search selection, exact size, quantity and multiple draft rows. Inventory remains unchanged until confirmation. The browser test entered L × 2, left for a sale, returned, refreshed, continued the draft and confirmed once; S decreased only for the sale and L increased only for the receipt. Database tests cover normal/multiple-size stock, duplicate submission and healthy aggregate totals. Network uncertainty preserves the original submission; local drafts are scoped to the account/store/device. Auth interruption no longer clears a valid session.

Opening CSV/XLSX validation, error handling, shared sizes, atomic confirm, lots/movements, retry and reversal have regression coverage. Browser download/upload/preview passed. On 13 September, before the later header/build-tool changes, a separate **20,000-row, 1,000-product, 20,000-piece** database run completed preview in **2.66 seconds** and posting in **396.73 seconds**, with no duplicate on repeated confirmation and healthy reconciliation. [Capacity evidence](evidence/final-capacity.txt). That test used an explicit isolated-test backup bypass; it does not satisfy live backup prerequisites. The real server may hit an HTTP timeout on a long confirmation; inspect/retry the same import, never create a duplicate to work around it. Real server load acceptance remains outstanding.

## 11. Purchases

- **Formal:** real PDF upload, extraction, recovered header edits, exact shared M selection, atomic save and confirmation passed in both browsers. Database regression verifies extracted review lines materialize without stock posting; stale or invalid saves roll back.
- **Quick:** optional supplier/invoice/payment/photo, exact XL quantity and confirmation passed; purchase/stock/ledger/audit evidence is tested.
- **Photo:** reload recovery and subsequent upload passed in Chromium and WebKit. Scanned-image PDF OCR ran inside the actual Docker backend with Poppler/Tesseract; supplier/invoice extraction passed and stock/history remained unchanged. [OCR evidence](evidence/final-ocr.txt). Poor real invoices still require staff review/manual correction.
- **Supplier return:** linked original purchase items, exact quantities, reason/credit note, stock reduction, supplier credit and retry limits passed database tests. This is a purchase return, not a generic stock correction.

## 12. Returns

Sellable returns restore exact-size stock; damaged returns refund without adding sellable stock. Partial discounts use original paid values. Exchange links the returned and replacement movements in one atomic operation, including same-customer credit exchanges. Insufficient replacement stock/credit rolls back both sides. Void restores inventory once, and repeat requests preserve one result. Regression tests passed for each; physical customer-policy acceptance remains the owner's responsibility.

## 13. Printing

Configurable 80/58 mm receipt and independent label settings are implemented. Receipts retain size, brand, price, discounts, tax/HSN where recorded, payment/reference and store policy/contact details. Reprinting does not call the sale-creation API. Labels support 50×30, 40×30 and 40×20 mm, exact-size context, MRP/barcode and no purchase cost. Both browsers opened actual receipt and label preview documents.

Browser/system printing is the default, with separate receipt and label settings. No proprietary printer dependency is imposed. **Physical output, alignment, barcode readability, reconnect and drawer behavior are unverified.** The automation suppresses the OS print dialog; preview success is not a printed-paper pass.

## 14. Backup

A nonempty **285,255-byte** custom PostgreSQL archive restored to a newly created isolated database at head 0053. It retained 2 products, 8 variants, 47 movements, 18 sales and 13 purchases; inventory was healthy. **14 uploaded files** restored with byte-for-byte hash equality. [Restore evidence](evidence/final-restore.json).

This is the completed local synthetic rehearsal, not the live shop backup. Production database/media coverage, offsite upload and restore, actual retention, backup-age monitoring, disk/failure alert delivery and recovery ownership require external verification. No alert message was sent. No restore targeted production.

## 15. Docker

**Test Compose build PASS. Production Compose build PASS.** [Test build](evidence/final-docker.txt), [production build](evidence/final-production-build.txt). The earlier download timeout was resolved; it was a registry/network failure. The candidate builds with Node 22 and the backend image includes Tesseract and Poppler. Production Compose was built using disposable configuration; production services were not started.

## 16. Test environment

Local deployment: `rainbow_master_verification`, loopback `http://127.0.0.1:8099`, synthetic PostgreSQL database and private temporary uploads/import/status paths. Backend/frontend/database are healthy; `/health/live` returns `ok`, `/health/ready` returns `ready`, and login plus actual workflows passed. [Deployment evidence](evidence/final-deployment.json).

`/version` reports `git_sha: unknown`, `environment: testing`. This working-tree deployment is therefore **not an exact committed-release attestation**. GitLab authentication was unavailable (`glab auth status` exited 1); no remote TEST deployment/pipeline was claimed. A reviewed commit, remote TEST pipeline and matching version SHA remain required. Production health/version was not queried or changed during certification.

## 17. External verification

Required evidence that cannot be supplied by the local tests:

- Reviewed committed candidate, current remote CI/TEST deployment and matching version SHA.
- Migration rehearsal on an access-controlled actual production backup; production host health/security/version review before opening inventory.
- Actual database and complete media backup, offsite restore, retention and age checks; verified disk and backup-failure alerts.
- Real receipt/label printer and scanner, reconnect behavior and drawer if used.
- Actual shop Safari/tablet/keyboard and representative staff usability/accessibility acceptance; automation used Chromium and WebKit, not the shop hardware.
- Representative supplier photos, tax/payment/ledger totals, closing and each staff role accepted in TEST; production-size operational load and long-import timeout handling.

## 18. Production blockers

**CRITICAL:** exact remote release and migration rehearsal; current production/offsite recovery and alert evidence; production host readiness. Real opening inventory remains blocked until these pass.

**IMPORTANT:** physical receipt/label/scanner and actual Safari/tablet acceptance; representative staff/financial/OCR UAT; large-store response time and operational-load verification. Hardware checks may be waived only for an explicitly unused device, not falsely marked PASS.

**OPTIONAL:** model-specific printer SDK integration once a supported model is supplied; additional analytics and broader performance optimization after measured need. These optional additions do not replace required acceptance checks.

## 19. Inventory entry readiness

**CAN THE OWNER START ENTERING REAL OPENING INVENTORY? NO.**

Clear the critical release/recovery/host blockers and complete the required shop acceptance in section 17. Then approve only the **10-product pilot**, followed by 50–100 variants, one complete category/brand, and the remaining full shop. Every stage requires physical recount, zero unexplained discrepancies and owner sign-off. [Exact four-stage procedure](OPERATOR-GUIDE.md#four-stage-real-inventory-pilot), [activation and rollback checklist](RELEASE-CHECKLIST.md). Training with synthetic inventory in the local TEST environment can continue now.

## 20. Final recommendation

**NO-GO**
