from fastapi.testclient import TestClient

from app.main import app


def test_data_protection_status_requires_authentication() -> None:
    response = TestClient(app).get("/api/v1/admin/data-protection/status")

    assert response.status_code == 401


def test_manual_backup_action_requires_authentication() -> None:
    response = TestClient(app).post("/api/v1/admin/data-protection/backup/full")

    assert response.status_code == 401
