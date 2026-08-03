from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.schemas.backup import BackupComponentStatus, BackupStatusRead

logger = logging.getLogger(__name__)

STATUS_FILES = {
    "database": ("latest-database-backup.json",),
    "uploads": ("latest-upload-manifest.json", "latest-uploads-backup.json"),
    "offsite": ("latest-offsite-backup.json",),
    "database_restore": ("latest-database-restore-test.json", "latest-restore-test.json"),
    "upload_restore": ("latest-upload-restore-test.json",),
    "retention": ("latest-retention-report.json",),
    "health": ("backup-health-state.json",),
    "disk": ("latest-disk-status.json",),
}


class BackupStatusService:
    """Read host-produced status files without exposing paths, secrets, or logs."""

    def __init__(self, status_dir: Path | None):
        self.status_dir = status_dir

    def status(self) -> BackupStatusRead:
        if self.status_dir is None:
            return BackupStatusRead(configured=False, components=[])

        components: list[BackupComponentStatus] = []
        for component, filenames in STATUS_FILES.items():
            path = next((self.status_dir / filename for filename in filenames if (self.status_dir / filename).is_file()), None)
            if path is None:
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
                        "timestamp", "started_at", "finished_at", "checked_at", "file", "backup_file",
                        "dump_filename", "dump_size_bytes", "file_size_bytes", "sha256", "snapshot_id",
                        "duration_seconds", "table_count", "row_counts", "usage_percent", "available_kb",
                        "product_image_count", "brand_logo_count", "total_file_count", "mode", "message",
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
