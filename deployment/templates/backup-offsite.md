# Encrypted Offsite Backup Setup

Use Restic with a repository dedicated to Rainbow Fashions backups. Create
`/opt/rainbow-fashions/shared/backup-offsite.env` from the adjacent example,
set its mode to `0600`, and never copy it into a release or CI artifact.

The nightly uploader accepts only verified local database dumps with matching
checksum and metadata files, plus upload archives with manifests. It uploads
them using Restic client-side encryption and writes only a redacted repository
identifier and snapshot ID to backup status evidence.

Before enabling the offsite timer, initialise and test the intended repository
as an operator on the production host:

```bash
chmod 600 /opt/rainbow-fashions/shared/backup-offsite.env
source /opt/rainbow-fashions/shared/backup-offsite.env
restic init
restic snapshots
```

Do not enable remote pruning until the retention dry-run has been reviewed.
`prune_offsite_backups.sh` is dry-run by default and additionally requires
`OFFSITE_RETENTION_APPROVED=YES` with `--execute` before `restic --prune`.
