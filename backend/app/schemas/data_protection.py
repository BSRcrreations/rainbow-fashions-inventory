from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.schemas.backup import BackupStatusRead


class BackupJobRead(BaseModel):
    id: UUID
    job_type: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    local_file_path: Optional[str]
    remote_file_path: Optional[str]
    file_size_bytes: Optional[int]
    checksum: Optional[str]
    retention_until: Optional[datetime]
    error_message: Optional[str]

    model_config = {"from_attributes": True}


class DataProtectionStatusRead(BaseModel):
    backup: BackupStatusRead
    retention_days: int
    manual_actions_enabled: bool
    recent_failures: list[BackupJobRead]
