from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BackupComponentStatus(BaseModel):
    component: str
    status: str
    available: bool = True
    details: dict[str, Any] = Field(default_factory=dict)


class BackupStatusRead(BaseModel):
    configured: bool
    components: list[BackupComponentStatus]
    health: str = "WARNING"
    restore_proven: bool = False
    posting_allowed: bool = False
    issues: list[str] = Field(default_factory=list)
