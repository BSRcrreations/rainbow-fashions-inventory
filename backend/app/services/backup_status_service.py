from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.schemas.backup import BackupComponentStatus, BackupStatusRead

logger = logging.getLogger(__name__)

STATUS_FILES = {
    "database": "latest-database-backup.json",
    "uploads": "latest-uploads-backup.json",
    "offsite": "latest-offsite-backup.json",
    "restore_test": "latest-restore-test.json",
    "disk": "latest-disk-status.json",
}


class BackupStatusService:
    """Read host-produced status files without exposing paths, secrets, or logs."""

    def __init__(self, status_dir: Path | None):
        self.status_dir = status_dir

    def status(self) -> BackupStatusRead:
        if self.status_dir is None:
            return BackupStatusRead(configured=False, components=[])

        components: list[BackupComponentStatus] = []
        for component, filename in STATUS_FILES.items():
            path = self.status_dir / filename
            if not path.is_file():
                components.append(BackupComponentStatus(component=component, status="unknown", available=False))
                continue
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(raw, dict):
                    raise ValueError("status document must be an object")
                # Keep this endpoint deliberately restricted to operational metadata.
                details: dict[str, Any] = {
                    key: value
                    for key, value in raw.items()
                    if key
                    in {
                        "started_at", "finished_at", "checked_at", "file", "backup_file",
                        "file_size_bytes", "sha256", "snapshot_id", "duration_seconds",
                        "table_count", "usage_percent", "available_kb", "message",
                    }
                }
                components.append(
                    BackupComponentStatus(
                        component=component,
                        status=str(raw.get("status", "unknown")),
                        details=details,
                    )
                )
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                logger.warning("Could not read backup status for %s: %s", component, exc)
                components.append(BackupComponentStatus(component=component, status="unknown", available=False))
        return BackupStatusRead(configured=True, components=components)
