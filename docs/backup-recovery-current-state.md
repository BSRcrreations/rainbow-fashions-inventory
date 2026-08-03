# Backup and Recovery Current State

Audit date: 2026-08-03. Scope: production host `178.238.237.182`, application root `/opt/rainbow-fashions`.

## Production Evidence Attempt

A read-only SSH audit was attempted with the configured migration key. The host rejected authentication with `Permission denied (publickey,password)` before any command executed. No timer, backup directory, container, volume, cron, log, offsite, restore-test, or alert evidence was read from production. No production data or service was modified.

An authorized production operator must run the read-only commands in the runbook and retain redacted output before a requirement can move to `PROVEN`.

## Repository Findings

| Requirement | Status | Evidence / gap |
| --- | --- | --- |
| Daily PostgreSQL backup capability | CONFIGURED_NOT_PROVEN | `deployment/scripts/backup_postgres.sh` creates verified custom dumps, checksums and metadata under the required production backup root. No production run exists. |
| Daily backup timer | CONFIGURED_NOT_PROVEN | `rainbow-database-backup.timer` schedules 02:00 with persistence and jitter. Timer state is unknown. |
| Product images and brand logos | PARTIAL | Product images use the uploads bind mount. Brand logos currently use the product upload path. The upload backup detects the actual mounted source and emits counts, but no production manifest exists. |
| Invoice and other uploads | CONFIGURED_NOT_PROVEN | The complete backend uploads mount is archived, excluding temporary/cache content. No production archive exists. |
| Off-VPS encrypted storage | CONFIGURED_NOT_PROVEN | Restic tooling and protected-file template exist; no repository, snapshot, or `restic check` evidence exists. |
| Local retention | CONFIGURED_NOT_PROVEN | Dry-run-first retention script and timer exist. No reviewed dry-run report exists. |
| Offsite retention | CONFIGURED_NOT_PROVEN | Restic policy exists; destructive prune remains opt-in after review. No production report exists. |
| Weekly isolated database restore | CONFIGURED_NOT_PROVEN | A no-port, no-production-network temporary container drill is implemented. No completed restore report exists. |
| Upload restore test | CONFIGURED_NOT_PROVEN | Manifest-checked temporary sample restore is implemented. No completed report exists. |
| Alerting | MISSING | A protected generic webhook is supported, but no configured channel, delivery test, acknowledgement, or recovery evidence exists. |
| Backup health monitoring | CONFIGURED_NOT_PROVEN | A 15-minute health unit and evidence checks exist. No production status is available. |
| Production evidence report | CONFIGURED_NOT_PROVEN | Generator exists, but no current evidence report exists. |
| GitLab read-only verification job | CONFIGURED_NOT_PROVEN | `verify_production_backup_recovery` is manual-only on the protected deployment branch and retains redacted artifacts for 30 days. It has not executed in production. |

## Operational Classification

**AT_RISK**. None of the mandatory production protection requirements are `PROVEN`: there is no verified production dump, offsite snapshot, restore drill, image restore drill, retention review, or acknowledged alert evidence.

## Non-Production Validation

The isolated UAT PostgreSQL stack successfully created and checked a custom dump,
then restored it to a temporary no-network container. The test restored required
tables, recorded Alembic revision `20260803_0037`, and removed the temporary
container and volume. This validates the implementation path only; it is not
evidence of production backup protection. macOS Docker Desktop does not expose
the UAT named upload volume as a host-readable path, so the uploads archive and
image restore drill could not be run locally.

## Safe Next Production Audit

Once an authorized key or console session is available, run only these read-only commands first:

```bash
systemctl list-timers --all | grep -i rainbow || true
systemctl list-unit-files | grep -i rainbow || true
crontab -l || true
ls -lah /opt/rainbow-fashions/backups || true
find /opt/rainbow-fashions/backups -maxdepth 4 -type f | head -100
cd /opt/rainbow-fashions/current && docker compose ps
docker volume ls
```

Do not run a restore, a production import, `docker compose down -v`, a volume deletion, or retention with `--execute` as part of this audit.
