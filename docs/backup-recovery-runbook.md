# Backup and Recovery Runbook

## Recovery Objectives

- Recommended RPO: **24 hours** while daily backups are the only operational recovery points.
- RTO: **not yet measured**. Record the first successful isolated database and uploads restore duration before setting a production target.

The system remains `AT_RISK` until its evidence report says `PROTECTED`. Scripts alone are not operational proof.

## Protected Host Files

| File | Purpose | Mode |
| --- | --- | --- |
| `/opt/rainbow-fashions/shared/backend.env` | PostgreSQL identity and application environment | `0600` |
| `/opt/rainbow-fashions/shared/backup-offsite.env` | Restic repository credentials | `0600` |
| `/opt/rainbow-fashions/shared/backup-alerts.env` | Alert channel and thresholds | `0600` |

Never place these files in Git, release artifacts, CI artifacts, tickets, or chat.

## First Production Proof

Install the reviewed units from the active release, then reload systemd:

```bash
cp deployment/systemd/rainbow-database-backup.service /etc/systemd/system/
cp deployment/systemd/rainbow-database-backup.timer /etc/systemd/system/
cp deployment/systemd/rainbow-media-backup.service /etc/systemd/system/
cp deployment/systemd/rainbow-media-backup.timer /etc/systemd/system/
cp deployment/systemd/rainbow-offsite-backup.service /etc/systemd/system/
cp deployment/systemd/rainbow-offsite-backup.timer /etc/systemd/system/
cp deployment/systemd/rainbow-backup-restore-test.service /etc/systemd/system/
cp deployment/systemd/rainbow-backup-restore-test.timer /etc/systemd/system/
cp deployment/systemd/rainbow-backup-retention.service /etc/systemd/system/
cp deployment/systemd/rainbow-backup-retention.timer /etc/systemd/system/
cp deployment/systemd/rainbow-backup-health.service /etc/systemd/system/
cp deployment/systemd/rainbow-backup-health.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now rainbow-database-backup.timer rainbow-media-backup.timer rainbow-offsite-backup.timer rainbow-backup-restore-test.timer rainbow-backup-retention.timer rainbow-backup-health.timer
```

1. Confirm the production uploads bind mount with Docker inspection; do not assume a volume name.
2. Install systemd units, run `systemctl daemon-reload`, then enable only timers whose configuration is ready.
3. Start the database backup service and verify unit status, dump, checksum, metadata, and `pg_restore --list`.
4. Start the uploads backup service and inspect its product-image and brand-logo counts.
5. Initialise the reviewed dedicated Restic repository, run offsite backup, then verify `restic snapshots` and `restic check`.
6. Run `test_database_restore.sh`; retain its report with required table counts and duration.
7. Run `test_upload_restore.sh`; retain checksum evidence for product and brand samples.
8. Run retention scripts without `--execute` and review the dry-run results.
9. Configure an authorized alert channel, run `check_backup_health.sh --test-alert`, and obtain acknowledgement.
10. Run `generate_backup_evidence_report.sh`. Only `PROTECTED` is an acceptable operational result.

## Database Incident Recovery

1. Declare the incident and record the requested recovery point, selected dump, checksum, timestamp, and owner.
2. Retrieve the recovery set from Restic to a new incident directory. Verify its checksum and run `pg_restore --list`.
3. Run the isolated restore test before touching production.
4. Stop writes and take a fresh verified production backup as the rollback point.
5. Use an approved maintenance window and an explicit-confirmation restore command. Restore only the selected production database.
6. Restart the application. Verify `/health/ready`, Alembic revision, login, and critical stores/users/products/variants/barcodes/inventory/sales/purchases counts.
7. Retain the fresh pre-restore backup. If validation fails, decide whether to restore it and record the decision.

## Upload Incident Recovery

1. Restore an offsite snapshot to a new empty incident directory.
2. Check product and brand samples against the matching upload manifest.
3. Copy to a staging directory first and inspect ownership, paths, and permissions.
4. Preserve the current upload tree before synchronising. Do not use a delete option without incident-owner approval.
5. Verify product images, brand logos, and invoice retrieval after restart.

## Escalation and Evidence

Escalate SSH, Restic, alert-recipient, DNS, or reverse-proxy access to the authorized infrastructure owner. Retain the selected snapshot ID, checksum/dump-list results, restore start/end/duration, row counts, upload checksum results, deployed commit, Alembic revision, maintenance decisions, and final health checks.
