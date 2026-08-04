# Repository hardening final report

Date: 2026-08-04
Status: **NOT READY**

## 1. Executive summary

The application code-level checks completed successfully, but release readiness is blocked by tracked sensitive-artifact risk and unavailable disposable-infrastructure verification. No production system, credential, upload, invoice, or database was accessed or changed for this assessment.

## 2. Commit SHA tested

The implementation chain was tested at `84dce6ba74cc9a8cdffb7461acc29c9c5edc26ee` on the local `chore/alembic-schema-source-of-truth` branch. `origin/main` remained at `54cf706a30c0e30c8db18a82f389a66eed16caee`; therefore the prerequisite local changes have not been confirmed merged upstream.

## 3. Security status

**Failed / blocked.** The tracked tree includes an environment file whose filename has trailing whitespace, two database dump files, SQL seed material, and upload placeholder directories. Contents were deliberately not displayed or copied. A filename-only credential-pattern review also found the tracked environment file among files requiring remediation review. Prior local commits exist for credential cleanup, environment-file removal, and password-probe removal, but they are not merged into the inspected upstream branch. The controlled history rewrite and credential rotation remain unverified.

`gitleaks` and `trufflehog` were unavailable in this environment, so no approved secret-scanner pass can be claimed. `npm audit` completed with 3 moderate, 1 high, and 1 critical dependency advisory. A filename-only absolute-path review found legacy documentation/utility candidates that need review. No private-key filename was found.

## 4. Backend results

- Python compile check: passed.
- Full pytest: **157 passed, 1 warning** (an Argon2 dependency deprecation warning).
- OpenAPI generation: passed.
- `/health/live`: passed with HTTP 200 using the application test client.
- `/health/ready`: returned HTTP 503 because no disposable PostgreSQL service was configured; this is expected for the isolated worktree and does not prove deployed readiness.
- Existing tests cover store scoping, manager/owner authorization, destructive actions, backup-status access, stock corrections, opening-stock parsing, and reconciliation helper logic. Database-backed workflow coverage remains blocked below.

## 5. Frontend results

- `npm ci`: completed.
- `npm test`: **45 passed** in 8 files.
- `npm run lint`: passed.
- `npm run typecheck`: passed.
- `npm run build`: passed; the build emitted a non-failing JavaScript chunk-size warning.
- Login prefill pattern check found no credential prefill. Owner-only pages use the established role-protected API/UI pattern. A filename/import heuristic identified legacy page candidates for manual orphan-page review; it is not a conclusive runtime-route audit.

## 6. Database migration results

- Alembic has one head: `20260804_0039`.
- The read-only schema verifier confirmed the single head.
- Docker now relies on backend startup migration rather than `schema.sql` or `seed.sql` mounts.
- Fresh migration, representative legacy upgrade, ORM-vs-live schema comparison, and generated snapshot comparison were **not run**: no disposable PostgreSQL database or safe backend environment configuration was available.

## 7. Inventory workflow results

The code and unit suite cover stock corrections, destructive/void behavior, barcode/store scoping, opening-stock parser validation, and reconciliation classifications. The full end-to-end workflow (bootstrap through sale, return, adjustment, reconciliation, and strict import) was **not run** because it requires a disposable PostgreSQL stack. No production inventory was modified.

## 8. 20,000-row import results

The generated, non-sensitive CSV parser test accepted and normalized 20,000 rows in the backend test suite. The earlier focused parser measurement completed in approximately 0.47 seconds. A database-backed 20,000-row post, exact count/cost-lot/barcode reconciliation, idempotent retry, and injected-failure rollback were **not run** without disposable PostgreSQL infrastructure. Do not treat parser-only evidence as transactional import certification.

## 9. Backup/restore results

Backup and restore shell scripts passed syntax validation. Backup-status unit tests passed. Actual backup creation, restore, retention, offsite, disk-health, and restore-test execution were **not run**, because no disposable backup target or database was configured. This remains a production blocker.

## 10. Docker results

`docker compose config` could not run because the isolated worktree intentionally has no `backend/.env`. A clean stack start, migration execution, service health, upload persistence, restart persistence, and production no-seed confirmation were therefore not executed. The Docker configuration was statically inspected: PostgreSQL no longer receives schema/seed initialization mounts, and the backend entrypoint runs `alembic upgrade head` before Uvicorn.

## 11. Remaining production blockers

1. Remove/rewrite tracked environment material, database dumps, and trailing-whitespace filenames; rotate every potentially exposed credential.
2. Complete and verify the controlled Git-history remediation across all branches/tags; document collaborator recovery.
3. Merge the prerequisite cleanup/inventory commits into the reviewed upstream release branch.
4. Resolve the high and critical npm advisories or record a reviewed, time-bound exception.
5. Run an approved secret scanner against the rewritten repository and retain a redacted result.
6. Run fresh and representative Alembic migration tests plus the complete inventory/import workflow in disposable PostgreSQL/Docker infrastructure.
7. Run and verify backup/restore, upload persistence, disk, and health checks in disposable infrastructure.

## 12. Go/no-go recommendation

**NO-GO / NOT READY.** Do not deploy or import real opening stock until every blocker above is resolved and the missing disposable-infrastructure validations pass. This status intentionally does not claim live-production verification.
