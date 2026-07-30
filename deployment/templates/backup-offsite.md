# Encrypted offsite database backups

The offsite uploader uses [restic](https://restic.net/) so database backup
files are encrypted on the production server before they leave it. It uploads
only verified local database backups from:

```text
/opt/rainbow-fashions/backups/database
```

The uploader refuses `.partial` files and requires every dump to have a valid
`pg_restore --list` result, SHA-256 checksum, and metadata sidecar file. It
does not delete local backups.

## S3-compatible configuration

Choose and create the bucket/path with the storage provider first. Do not run
`restic init` until the bucket, endpoint, and access scope are confirmed. Copy
the safe template to the server and restrict it:

```bash
sudo cp deployment/templates/backup-offsite.env.example /opt/rainbow-fashions/shared/backup-offsite.env
sudo chmod 600 /opt/rainbow-fashions/shared/backup-offsite.env
```

Set `BACKUP_PROVIDER=s3`, the S3-compatible restic repository, a unique strong
`RESTIC_PASSWORD`, and provider credentials. Use a dedicated bucket and an
access key restricted to that bucket. The real file must never be committed or
stored in CI artifacts.

After confirming the exact target, initialize once and perform a manual upload:

```bash
source /opt/rainbow-fashions/shared/backup-offsite.env
restic init
/opt/rainbow-fashions/current/deployment/scripts/upload_backups_offsite.sh
restic snapshots
restic check
```

Never paste the environment file or its credential values into a terminal
transcript, ticket, or Git commit.

## SFTP alternative

Restic also supports SFTP repositories. Use a separate active configuration
containing only:

```text
BACKUP_PROVIDER=sftp
RESTIC_REPOSITORY=sftp:backup-user@backup-host:/srv/restic/rainbow-fashions
RESTIC_PASSWORD=<unique strong restic password>
```

Authenticate SFTP with a server-side SSH key configured by the administrator.
Do **not** include `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, or
`AWS_DEFAULT_REGION` in an SFTP configuration.

## Systemd installation

Install after the local daily database backup service is installed and tested:

```bash
sudo cp deployment/systemd/rainbow-offsite-backup.service /etc/systemd/system/
sudo cp deployment/systemd/rainbow-offsite-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rainbow-offsite-backup.timer
sudo systemctl list-timers rainbow-offsite-backup.timer
```

The timer runs at 03:00 server local time with up to 15 minutes of randomized
delay, after the expected 02:00 local database backup. `Persistent=true` runs
a missed schedule after the server returns. The script's `flock` lock prevents
overlapping uploads.
