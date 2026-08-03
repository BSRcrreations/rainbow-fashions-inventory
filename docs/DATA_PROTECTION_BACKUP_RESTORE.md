# Data protection, backup, and recovery

This runbook covers the Rainbow Fashions database and all user-uploaded media: product images, brand logos, invoice documents, and later upload directories beneath the same uploads root. It is designed to be installed and proven in **staging first**. Never use staging credentials, paths, dumps, or a restore command against production.

## What is protected

| Asset | Local copy | Remote copy | Retention |
| --- | --- | --- | --- |
| PostgreSQL | `/u02/backups/database/*.dump` in custom pg_dump format | encrypted Restic snapshot | 30 daily local and remote backups (plus 8 weekly remote points) |
| Application uploads | `/u02/backups/uploads/*.tar.gz` | encrypted Restic snapshot | 30 days |
| Operational status | `/u02/backups/status/*.json` | displayed to owners only | current state |

The database backup filename is `rainbow_inventory_db_YYYY-MM-DD_HH-MM-SS.dump`; upload archives are named `rainbow_inventory_uploads_YYYY-MM-DD_HH-MM-SS.tar.gz`. Each archive has a SHA-256 sidecar and owner-only permissions. Backups are written as `.partial` and atomically renamed only after PostgreSQL validates their contents.

## Initial staging setup

1. Install `postgresql-client`, `restic`, `curl`, and the system `tar` utility on the staging host.
2. Move uploads to a host path so the backup service can read them without entering a container. Create `/u02/rainbow/uploads`, copy the existing `backend_uploads` volume contents into it once, then set `UPLOADS_HOST_PATH=/u02/rainbow/uploads` for Compose. Do not use `--delete` while copying data. Configure `APPLICATION_UPLOAD_PATH` to this root so products, brands, invoices, OCR files, supplier documents, and future upload folders are all included. Alternatively configure the individual `*_PATH` settings and `ADDITIONAL_UPLOAD_PATHS`.
3. Create `/etc/rainbow-fashions/backup.env` from `deployment/templates/backup.env.example`, fill in staging-only values, then run `chmod 600 /etc/rainbow-fashions/backup.env`.
4. Create a dedicated PostgreSQL backup role with only the permissions needed by `pg_dump`, and create a `/etc/rainbow-fashions/pgpass` file with `0600` permissions. Do not put `PGPASSWORD` or a database password into a script, unit, repository, or shell history.
5. Create the dedicated, disposable staging database named exactly `rainbow_inventory_restore_test` (or another name ending `_restore_test`) and grant only its restore-test role access to it. It must not be a production database or production host.
6. Initialize the confirmed remote Restic repository once: `source /etc/rainbow-fashions/backup.env && restic init`. Use a bucket/key restricted to this backup repository.
7. Set `BACKUP_STATUS_DIR=/backup-status` in the backend environment and use `BACKUP_STATUS_HOST_PATH=/u02/backups/status` in Compose. This exposes only status metadata to owner accounts.

Validate, in this order, on staging:

```bash
bash -n deployment/scripts/backup_postgres.sh deployment/scripts/backup_uploads.sh deployment/scripts/upload_backups_offsite.sh deployment/scripts/test_backup_restore.sh
sudo BACKUP_CONFIG_FILE=/etc/rainbow-fashions/backup.env deployment/scripts/backup_postgres.sh
sudo BACKUP_CONFIG_FILE=/etc/rainbow-fashions/backup.env deployment/scripts/backup_uploads.sh
sudo BACKUP_CONFIG_FILE=/etc/rainbow-fashions/backup.env deployment/scripts/upload_backups_offsite.sh
sudo BACKUP_CONFIG_FILE=/etc/rainbow-fashions/backup.env deployment/scripts/test_backup_restore.sh
```

Inspect `systemctl status` and `/u02/backups/status/` after each. Confirm that the owner-only Security page reports database, uploads, offsite, restore-test, and disk statuses. Review this evidence before copying the reviewed configuration to production. The production restore-test timer must **not** be enabled; it belongs only on staging.

## Timers and monitoring

Install the systemd unit/timer pairs from `deployment/systemd/`, then use:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now rainbow-database-backup.timer rainbow-media-backup.timer rainbow-offsite-backup.timer rainbow-backup-disk-monitor.timer
sudo systemctl enable --now rainbow-backup-restore-test.timer # staging only
sudo systemctl list-timers 'rainbow-*backup*' 'rainbow-*restore*'
```

Database backup runs daily at 02:00, application-upload backup at 02:20, and encrypted upload at 03:00. Upload archives preserve directory structure and file timestamps, are verified with `tar --list`, and never modify source files. The staging restore drill runs every Sunday at 05:00 and fails closed unless its environment is exactly `staging`, its target name ends `_restore_test`, and the host is not production-like. Disk capacity is checked hourly; it exits non-zero when critical and optionally posts a credential-free alert to `BACKUP_ALERT_WEBHOOK_URL`.

## Restore procedure

Restores are destructive. Designate an incident owner, record the requested recovery point, and stop the application before changing data.

1. Identify the desired dump and archive, then verify checksums and inspect the dump:

```bash
cd /u02/backups/database
sha256sum --check rainbow_inventory_db_YYYY-MM-DD_HH-MM-SS.dump.sha256
pg_restore --list rainbow_inventory_db_YYYY-MM-DD_HH-MM-SS.dump >/dev/null
```

2. **Prove the recovery point in staging first.** Restore only to the disposable `_restore_test` database with `test_backup_restore.sh`, confirm table counts and a representative product/invoice, and test extracting the matching uploads archive into a temporary directory.
3. Notify users, put the production application in maintenance mode, and take a fresh backup of the current production state. Keep it even if the incident restore proceeds.
4. Set `RESTORE_DB_HOST`, `RESTORE_DB_PORT`, `RESTORE_DB_NAME`, and `RESTORE_DB_USER` in the protected configuration. Run `restore_postgres.sh` with the exact selected dump. It verifies the checksum and requires the exact database name confirmation before it uses `pg_restore --clean`.
5. Restore uploads to a new temporary directory first, inspect ownership and contents, then synchronise them into the uploads root. Do not use `rsync --delete` until the incident owner has verified the target and rollback plan. Preserve a timestamped copy of the current uploads tree.
6. Start the app, run `/health/ready`, confirm login, product images, brand logos, and invoice retrieval, then record the dump checksum, uploads archive checksum, timings, and validation result in the incident record.

### Retrieving an offsite recovery point

Use Restic only from the protected configuration. List snapshots, restore the selected snapshot into a new empty directory, then perform the same checksum and staging validation above:

```bash
source /etc/rainbow-fashions/backup.env
restic snapshots --tag rainbow-fashions
restic restore <snapshot-id> --target /u02/recovery/<incident-id>
```

Never place a production dump in a ticket, CI artifact, source tree, or shared chat channel.
