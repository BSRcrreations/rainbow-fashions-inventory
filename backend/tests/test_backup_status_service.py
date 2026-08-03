import json

from fastapi.testclient import TestClient

from app.main import app
from app.services.backup_status_service import BackupStatusService


def test_status_is_not_configured_without_a_host_mount() -> None:
    status = BackupStatusService(None).status()

    assert status.configured is False
    assert status.components == []


def test_status_reads_only_safe_operational_metadata(tmp_path) -> None:
    (tmp_path / "latest-database-backup.json").write_text(
        json.dumps(
            {
                "component": "database",
                "status": "success",
                "file": "rainbow_inventory_db_2026-08-03_02-00-00.dump",
                "sha256": "abc123",
                "database_url": "postgresql://must-not-be-returned",
                "secret": "must-not-be-returned",
            }
        ),
        encoding="utf-8",
    )

    status = BackupStatusService(tmp_path).status()
    database = next(component for component in status.components if component.component == "database")

    assert status.configured is True
    assert database.status == "success"
    assert database.details["sha256"] == "abc123"
    assert "database_url" not in database.details
    assert "secret" not in database.details


def test_invalid_status_file_is_reported_as_unknown(tmp_path) -> None:
    (tmp_path / "latest-disk-status.json").write_text("not json", encoding="utf-8")

    status = BackupStatusService(tmp_path).status()
    disk = next(component for component in status.components if component.component == "disk")

    assert disk.status == "unknown"
    assert disk.available is False


def test_status_reads_new_verified_backup_evidence_names(tmp_path) -> None:
    (tmp_path / "latest-upload-manifest.json").write_text(
        json.dumps(
            {
                "status": "SUCCESS",
                "product_image_count": "4",
                "brand_logo_count": "2",
                "manifest_path": "/opt/rainbow-fashions/backups/uploads/private.json",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "latest-database-restore-test.json").write_text(
        json.dumps({"status": "SUCCESS", "row_counts": "{\"products\": 10}"}),
        encoding="utf-8",
    )

    status = BackupStatusService(tmp_path).status()

    uploads = next(component for component in status.components if component.component == "uploads")
    restore = next(component for component in status.components if component.component == "database_restore")
    assert uploads.status == "SUCCESS"
    assert uploads.details == {"product_image_count": "4", "brand_logo_count": "2"}
    assert restore.details == {"row_counts": "{\"products\": 10}"}


def test_backup_status_endpoint_requires_authentication() -> None:
    response = TestClient(app).get("/api/v1/security/backup-status")

    assert response.status_code == 401
