# Backup and restore runbook

This is the operator entry point for the Rainbow Fashions data-protection system. Read the detailed [data protection runbook](DATA_PROTECTION_BACKUP_RESTORE.md) before enabling any service on production.

Daily at 02:00, `rainbow-backup.service` creates a custom PostgreSQL dump and a timestamp-preserving upload archive, verifies both, and only then runs retention cleanup. Dumps are in `/u02/backups/database`; uploaded files are in `/u02/backups/uploads`; logs and current status files are under `/u02/backups/logs` and `/u02/backups/status`. The remote uploader runs separately after local verification.

## Installation and staging promotion

On the **staging** host, create the restricted account, protect the configuration, install the reviewed units, and enable the timers:

```bash
sudo useradd --system --home /nonexistent --shell /usr/sbin/nologin rainbow-backup
sudo install -d -o rainbow-backup -g rainbow-backup -m 0700 /u02/backups /u02/rainbow/uploads
sudo install -m 0600 deployment/templates/backup.env.example /etc/rainbow-fashions/backup.env
sudo cp deployment/systemd/rainbow-backup.{service,timer} /etc/systemd/system/
sudo cp deployment/systemd/rainbow-restore-test.{service,timer} /etc/systemd/system/
sudo cp deployment/systemd/rainbow-disk-monitor.{service,timer} /etc/systemd/system/
sudo cp deployment/systemd/rainbow-offsite-backup.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rainbow-backup.timer rainbow-disk-monitor.timer rainbow-offsite-backup.timer rainbow-restore-test.timer
```

Enable `rainbow-backup-job-runner.timer` only after testing the host-side job role and then enabling manual actions in the backend environment. Do not enable the restore-test timer on production until it points exclusively to a staging restore database. Promote the same reviewed scripts/configuration only after staging backup, remote upload, restore, image retrieval, and alert tests succeed.

## Safe manual verification

```bash
cd /u02/backups/database
sha256sum --check rainbow_inventory_db_YYYY-MM-DD_HH-MM-SS.dump.sha256
pg_restore --list rainbow_inventory_db_YYYY-MM-DD_HH-MM-SS.dump >/dev/null

cd /u02/backups/uploads
sha256sum --check rainbow_inventory_uploads_YYYY-MM-DD_HH-MM-SS.tar.gz.sha256
tar --list --gzip --file=rainbow_inventory_uploads_YYYY-MM-DD_HH-MM-SS.tar.gz >/dev/null
```

To prove a database recovery, always restore into a new database first:

```bash
createdb rainbow_inventory_restored
pg_restore --clean --if-exists --no-owner --dbname=rainbow_inventory_restored /u02/backups/database/rainbow_inventory_db_TIMESTAMP.dump
```

Never restore directly into production without an approved maintenance window, a fresh rollback backup, a verified staging restore, and a documented rollback owner. For uploads, extract into an empty temporary directory, inspect the tree and timestamps, then copy it into the application upload root only after preserving the current uploads tree.

## Remote storage and operations

Keep S3/Restic credentials only in `/etc/rainbow-fashions/backup.env` (`0600`). Use HTTPS endpoints and server-side encryption configured at the bucket/provider. Rotate storage credentials by creating a new scoped key, validating the staging upload and restore, updating the protected file, then revoking the old key only after a successful production upload.

Review `systemctl status rainbow-backup.service`, `/u02/backups/logs/`, and the owner-only **Settings → Data Protection** status before escalating failures. Test changes in staging, including the weekly restore timer and image/invoice retrieval, before copying the reviewed configuration to production.

Manual actions are queued by the owner-only Data Protection page and executed by the separate `rainbow-backup-job-runner.timer`; the API never executes a host command. Enable `BACKUP_MANUAL_ACTIONS_ENABLED=true` only after the job-runner database role and timer have been installed and tested in staging.
