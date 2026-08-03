# Release Readiness

## Result: NOT READY

Date: 2026-08-03

The application is suitable for continued isolated UAT, but it must not be
promoted to staging or production yet.

## Gates

| Gate | Result | Evidence |
| --- | --- | --- |
| No unresolved inventory-integrity blocker | FAIL | Active models rely on schema supplied by untracked migration `20260803_0037`. |
| Cart items visible | PASS | Exact M variant visible in Current Sale during UAT-004. |
| Product editing works without direct stock edit | PASS | UAT-002 persisted name through refresh. |
| Barcode staging and repeat scans work | PASS | UAT-007 accumulated 2 scans in one row. |
| Exact-variant stock posting works | PASS | UAT-006 and UAT-008 verified variant stock changes. |
| Percentage discount works | PASS | UAT-005 calculated 10% correctly. |
| Automated tests pass | PASS | 148 backend, 49 frontend tests. |
| Lint and TypeScript pass | PASS | `npm run lint`, `npm run typecheck` passed. |
| Production frontend build passes | PASS WITH WARNING | Build passed; Vite reports a 594 KB bundle. |
| Alembic migrations reviewed and reproducible | FAIL | Tracked head is `0036`; active schema change is untracked as `0037`. |
| Backup restore drill | FAIL | No isolated restore execution evidence. |
| Safari and Chromium browser checks | INCOMPLETE | Only the in-app browser was available. |

## Required Before Staging

1. Review, commit, and test migration `0037` with all dependent model, schema,
   route, and frontend changes.
2. Rebuild the UAT image from committed files only, create a fresh test
   database through the supported migration path, and re-run the complete
   checklist.
3. Add and pass cross-store and role-denial browser/API checks.
4. UAT stock reset, adjustment/correction, sale void/return, purchase OCR, and
   invoice confirmation using disposable fixtures.
5. Run and record a backup restore drill.

## Recommended Merge Path

`test/inventory-uat` -> `shop-inventory`

Only after integration verification and an explicit release review:

`shop-inventory` -> `main`
