from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import READY_TABLES, app


client = TestClient(app)


def test_liveness_health_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "backend"


def test_liveness_alias_returns_ok() -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "backend"}


def test_readiness_health_returns_ok_when_database_query_succeeds() -> None:
    connection = MagicMock()
    select_result = MagicMock()
    select_result.scalar.return_value = 1
    connection.execute.return_value = select_result
    connection_context = MagicMock()
    connection_context.__enter__.return_value = connection

    with patch("app.main.engine.connect", return_value=connection_context):
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "backend"}
    assert str(connection.execute.call_args_list[0].args[0]) == "SELECT 1"
    assert connection.execute.call_count == len(READY_TABLES) + 1


def test_api_health_alias_uses_database_readiness_check() -> None:
    connection = MagicMock()
    select_result = MagicMock()
    select_result.scalar.return_value = 1
    connection.execute.return_value = select_result
    connection_context = MagicMock()
    connection_context.__enter__.return_value = connection

    with patch("app.main.engine.connect", return_value=connection_context):
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "backend"}


def test_readiness_health_hides_database_errors() -> None:
    database_secret = "postgresql+psycopg://inventory_user:never-disclose@postgres:5432/inventory_db"

    with patch("app.main.engine.connect", side_effect=RuntimeError(f"connection failed: {database_secret}")):
        response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"
    assert response.json()["service"] == "backend"
    assert database_secret not in response.text
    assert "traceback" not in response.text.lower()
