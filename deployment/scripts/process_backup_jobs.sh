#!/usr/bin/env bash
# Privileged host-side executor for owner-queued jobs. The web application only
# inserts pending rows; it never invokes host commands directly.
set -Eeuo pipefail
CONFIG_FILE="${BACKUP_CONFIG_FILE:-/etc/rainbow-fashions/backup.env}"
[[ -r "$CONFIG_FILE" ]] || { echo "Missing backup configuration" >&2; exit 2; }
source "$CONFIG_FILE"
: "${BACKUP_JOB_DB_HOST:?BACKUP_JOB_DB_HOST is required}"
: "${BACKUP_JOB_DB_PORT:=5432}"
: "${BACKUP_JOB_DB_NAME:?BACKUP_JOB_DB_NAME is required}"
: "${BACKUP_JOB_DB_USER:?BACKUP_JOB_DB_USER is required}"
: "${BACKUP_LOCAL_PATH:=/u02/backups}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; LOG_DIR="$BACKUP_LOCAL_PATH/logs"; mkdir -p "$LOG_DIR"; chmod 700 "$LOG_DIR"
LOG_FILE="$LOG_DIR/manual-job-runner.log"; touch "$LOG_FILE"; chmod 600 "$LOG_FILE"
log() { printf '%s manual-job-runner %s\n' "$(date --iso-8601=seconds 2>/dev/null || date)" "$*" | tee -a "$LOG_FILE" >&2; }
psql_job() { psql --host="$BACKUP_JOB_DB_HOST" --port="$BACKUP_JOB_DB_PORT" --username="$BACKUP_JOB_DB_USER" --dbname="$BACKUP_JOB_DB_NAME" "$@"; }

# SKIP LOCKED guarantees only one executor claims a queued job, even if a timer
# fires again while another invocation is still running.
while IFS='|' read -r job_id job_type; do
  [[ -n "$job_id" ]] || continue
  log "running job=${job_id} type=${job_type}"
  case "$job_type" in
    database_backup) command=("$SCRIPT_DIR/backup_postgres.sh") ;;
    uploads_backup) command=("$SCRIPT_DIR/backup_uploads.sh") ;;
    full_backup) command=("$SCRIPT_DIR/backup_all.sh") ;;
    remote_upload) command=("$SCRIPT_DIR/upload_backups_offsite.sh") ;;
    restore_test) command=("$SCRIPT_DIR/test_backup_restore.sh") ;;
    *) psql_job --command "UPDATE backup_jobs SET status='failed', completed_at=now(), error_message='Unsupported backup job type' WHERE id='${job_id}'"; continue ;;
  esac
  if "${command[@]}" >> "$LOG_FILE" 2>&1; then
    psql_job --command "UPDATE backup_jobs SET status='success', completed_at=now() WHERE id='${job_id}'"
    log "job=${job_id} result=success"
  else
    psql_job --command "UPDATE backup_jobs SET status='failed', completed_at=now(), error_message='Host backup command failed; see manual-job-runner.log' WHERE id='${job_id}'" || true
    log "job=${job_id} result=failed"
  fi
done < <(psql_job --tuples-only --no-align --field-separator='|' --command "WITH next_job AS (SELECT id FROM backup_jobs WHERE status='pending' ORDER BY started_at FOR UPDATE SKIP LOCKED LIMIT 1) UPDATE backup_jobs AS job SET status='running' FROM next_job WHERE job.id=next_job.id RETURNING job.id, job.job_type;")
