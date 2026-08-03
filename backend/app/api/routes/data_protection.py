from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_owner
from app.core.config import get_settings
from app.core.exceptions import bad_request, conflict, not_found
from app.database.session import get_db
from app.models.backup_job import BackupJob
from app.models.user import User
from app.schemas.data_protection import BackupJobRead, DataProtectionStatusRead
from app.services.backup_status_service import BackupStatusService


router = APIRouter(prefix="/admin/data-protection", tags=["Data Protection"])
TERMINAL_STATUSES = {"success", "failed", "warning"}


@router.get("/status", response_model=DataProtectionStatusRead)
def status_overview(db: Session = Depends(get_db), _: User = Depends(require_owner)) -> DataProtectionStatusRead:
    settings = get_settings()
    failures = db.scalars(
        select(BackupJob).where(BackupJob.status.in_(("failed", "warning"))).order_by(BackupJob.started_at.desc()).limit(10)
    ).all()
    return DataProtectionStatusRead(
        backup=BackupStatusService(settings.backup_status_dir).status(),
        retention_days=settings.backup_retention_days,
        manual_actions_enabled=settings.backup_manual_actions_enabled,
        recent_failures=failures,
    )


@router.get("/jobs", response_model=list[BackupJobRead])
def list_jobs(limit: int = 50, db: Session = Depends(get_db), _: User = Depends(require_owner)) -> list[BackupJob]:
    return db.scalars(select(BackupJob).order_by(BackupJob.started_at.desc()).limit(min(max(limit, 1), 100))).all()


@router.get("/jobs/{job_id}", response_model=BackupJobRead)
def get_job(job_id: UUID, db: Session = Depends(get_db), _: User = Depends(require_owner)) -> BackupJob:
    job = db.get(BackupJob, job_id)
    if job is None:
        raise not_found("Backup job")
    return job


def enqueue_manual_job(job_type: str, db: Session, current_user: User) -> BackupJob:
    settings = get_settings()
    if not settings.backup_manual_actions_enabled:
        raise bad_request("Manual backup actions are disabled on this deployment.", "backup_actions_disabled")
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=settings.backup_manual_rate_limit_minutes)
    duplicate = db.scalar(
        select(BackupJob).where(
            BackupJob.job_type == job_type,
            BackupJob.status.in_(("pending", "running")),
            BackupJob.started_at >= cutoff,
        )
    )
    if duplicate:
        raise conflict("An equivalent backup job is already queued or running.", "backup_job_in_progress")
    job = BackupJob(job_type=job_type, status="pending", requested_by=current_user.id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.post("/backup/database", response_model=BackupJobRead, status_code=status.HTTP_202_ACCEPTED)
def queue_database_backup(db: Session = Depends(get_db), current_user: User = Depends(require_owner)) -> BackupJob:
    return enqueue_manual_job("database_backup", db, current_user)


@router.post("/backup/uploads", response_model=BackupJobRead, status_code=status.HTTP_202_ACCEPTED)
def queue_uploads_backup(db: Session = Depends(get_db), current_user: User = Depends(require_owner)) -> BackupJob:
    return enqueue_manual_job("uploads_backup", db, current_user)


@router.post("/backup/full", response_model=BackupJobRead, status_code=status.HTTP_202_ACCEPTED)
def queue_full_backup(db: Session = Depends(get_db), current_user: User = Depends(require_owner)) -> BackupJob:
    return enqueue_manual_job("full_backup", db, current_user)


@router.post("/test-remote", response_model=BackupJobRead, status_code=status.HTTP_202_ACCEPTED)
def queue_remote_test(db: Session = Depends(get_db), current_user: User = Depends(require_owner)) -> BackupJob:
    return enqueue_manual_job("remote_upload", db, current_user)


@router.post("/test-restore", response_model=BackupJobRead, status_code=status.HTTP_202_ACCEPTED)
def queue_restore_test(db: Session = Depends(get_db), current_user: User = Depends(require_owner)) -> BackupJob:
    return enqueue_manual_job("restore_test", db, current_user)


@router.get("/disk-usage")
def disk_usage(_: User = Depends(require_owner)) -> dict:
    state = BackupStatusService(get_settings().backup_status_dir).status()
    return next((component.model_dump() for component in state.components if component.component == "disk"), {"component": "disk", "status": "unknown", "available": False, "details": {}})
