# Encrypted offsite backups

Use [backup.env.example](backup.env.example) as the single protected backup
configuration. It contains the Restic repository settings alongside the local
database/uploads paths, monitoring thresholds, and staging-only restore target.

The uploader encrypts verified PostgreSQL custom-format dumps and uploaded-file
archives before upload, then keeps 30 daily remote recovery points and eight
weekly points. It never initializes a repository automatically: validate the
bucket or SFTP target and run `restic init` once as a reviewed operator action.

Install `rainbow-offsite-backup.service` and its timer only after the daily
database and uploads timers pass in staging. The full configuration, validation,
and recovery procedure is in
[`docs/DATA_PROTECTION_BACKUP_RESTORE.md`](../../docs/DATA_PROTECTION_BACKUP_RESTORE.md).
