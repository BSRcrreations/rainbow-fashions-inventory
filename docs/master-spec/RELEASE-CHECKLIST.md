# Release and rollback checklist

This checklist is a procedure, not authorization to deploy or alter production inventory. The current changes are an uncommitted working-tree candidate. No production deployment or production stock import was performed.

## Establish the exact candidate

1. Review `READINESS.md`, `MODIFIED-FILES.txt` and the source manifest. Review the full diff, especially historical migration changes, sales/returns, idempotency, permissions and cash reporting.
2. Commit the reviewed changes and record the new full SHA. The base SHA in this report is not the SHA of the changed candidate.
3. Run GitLab on that commit. Require backend/integration/concurrency tests, frontend tests, lint, typecheck, build, secrets/artifacts scans, dependency audit, one Alembic head and Docker build gates. Do not substitute an old readiness report or pipeline for this commit.
4. Test a restored, access-controlled copy of the actual database through the migration path. An unversioned nonempty database is deliberately rejected. Do not stamp an unknown database at head or use `create_all` as an upgrade.

## Backup and rehearsal prerequisites

Use the environment's existing protected backup configuration; do not put credentials in a release checkout. Review the scripts before running them on the target host. Run the configured database backup, uploads backup, offsite upload, database restore test and upload restore test. Inspect the resulting status documents, checksums and restore reports. Test backup-failure and disk alerts through the configured alert destination with explicit permission to send the test message.

Relevant existing scripts are `deployment/scripts/backup_postgres.sh`, `backup_uploads.sh`, `upload_backups_offsite.sh`, `test_database_restore.sh`, `test_upload_restore.sh`, `check_backup_health.sh` and `monitor_backup_disk.sh`. They depend on the host's configured backup environment. A mere nonempty dump from `backup_before_deploy.sh` does not replace these restore/offsite proofs.

Local evidence in this folder proves only synthetic data. Require current production-specific evidence before go-live. Verify invoices, product images and opening-import evidence directories are included in the recovery plan; a text-file upload rehearsal does not prove restoration of the real media collection.

## Test deployment

The repository's guarded GitLab `deploy_test` and `verify_test` jobs are the preferred remote TEST path. They use the test root, test Compose project and protected TEST owner variables. Do not run `reset_test_uat_data` as a normal deployment step.

Current local rehearsal: Compose project `rainbow_master_verification`, loopback URL `http://127.0.0.1:8099`, disposable PostgreSQL, separate uploads/import/status directories under `/private/tmp/rainbow-master-deployment`. It contains synthetic data only. Runtime credentials and dumps are outside the repository. This is not the remote test or production environment.

Before promotion, run the shop's UAT matrix on the exact committed build: all roles, metadata creation, unique/shared barcodes, scan/category/search billing, discounts/payment modes, quick/formal/photo purchases, stock entry and recovery, partial/damaged returns, exchange, void, supplier return, correction, closing, receipts/labels, Chrome, Safari and the actual tablet/scanner/printer. Check stock integrity after every stock-changing flow. Test real invoice examples and purchase totals, not just a clean generated image.

## Exact production activation procedure

Prefer the existing protected manual `deploy_production` job on the reviewed `main` commit, followed by `verify_production`. The job verifies deployment context, extracts the packaged release, backs up and invokes the activation script. Do not bypass a failed gate.

For an approved operator-run activation equivalent, execute from the reviewed release checkout on the configured production host. Set `CI_COMMIT_SHORT_SHA` to the reviewed artifact's commit and verify the artifact checksum first. Set `GIT_SHA` to its full SHA for version evidence.

```bash
export DEPLOY_ENVIRONMENT=production
export DEPLOY_PATH=/opt/rainbow-fashions-prod
export COMPOSE_PROJECT_NAME=rainbow_prod
export BACKEND_ENV_FILE=/opt/rainbow-fashions-prod/shared/backend.env
export COMPOSE_OVERRIDE=docker-compose.prod.yml
export LOCAL_DEPLOY_URL=http://127.0.0.1:8080
export PUBLIC_DEPLOY_URL=https://rainbow-fashions.in
export UPLOADS_HOST_PATH=/opt/rainbow-fashions-prod/runtime/uploads
export OPENING_STOCK_IMPORTS_HOST_PATH=/opt/rainbow-fashions-prod/runtime/opening-stock-imports
export BACKUP_STATUS_HOST_PATH=/opt/rainbow-fashions-prod/runtime/backups/status
export RELEASE_DIR="$DEPLOY_PATH/releases/$CI_COMMIT_SHORT_SHA"
bash deployment/scripts/verify_deployment_context.sh
install -d -m 750 "$RELEASE_DIR"
tar -xzf "rainbow-fashions-${CI_COMMIT_SHORT_SHA}.tar.gz" -C "$RELEASE_DIR"
bash "$RELEASE_DIR/deployment/scripts/backup_before_deploy.sh"
bash "$RELEASE_DIR/deployment/scripts/deploy_release.sh"
curl --fail --silent --show-error https://rainbow-fashions.in/health/live
curl --fail --silent --show-error https://rainbow-fashions.in/health/ready
curl --fail --silent --show-error https://www.rainbow-fashions.in/login
```

These commands depend on the existing protected environment, network/runner setup and approved backup/restore results. They are not an initial-server bootstrap recipe. Production credentials are never printed or committed. The activation script migrates both empty and versioned databases with Alembic, refuses unknown baselines, and restores the previous application symlink on activation failure. No opening stock or demo seed is part of deployment.

After activation, verify login, version SHA, all roles and read-only inventory integrity. Do not make synthetic sales or stock changes in production. Start real opening stock only after the owner approves the representative physical pilot described in the operator guide.

## Rollback

Stop new writes and preserve logs/request IDs before diagnosing a financial or stock problem. Record the current and previous release paths. For an application-only rollback, repoint `current` to the known previous release and start that release with the same explicit production Compose project, protected environment and mount paths. Verify health and version before reopening. Compatibility with new return/exchange rows must be checked; an older application may not understand the new workflows even if columns are additive.

Do not run Alembic downgrade to discard receipt, return, opening-import or audit evidence. New evidence-bearing migrations refuse destructive downgrades. Do not restore a pre-deploy database over later business transactions. If database recovery is necessary, restore into a separate database first, verify rows/media/integrity, reconcile transactions since the backup, and obtain an approved cutover plan. Retain both copies and the original evidence.

## Go-live decision

The owner and technical operator must sign off only when the exact committed candidate, actual production-clone upgrade, current offsite/restore/alerts, real hardware/browser UAT and production health/version checks all pass. Until then: **NO-GO for production opening stock**.
