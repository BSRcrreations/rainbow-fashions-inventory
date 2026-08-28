from __future__ import annotations

import logging
from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.api.deps import get_current_user
from app.api.routes import reports as reports_route
from app.database.session import get_db
from app.main import app
from app.services.report_service import ReportService


class _EmptyReportQuery:
    def filter(self, *args, **kwargs):
        return self

    def scalar(self):
        return 0

    def one(self):
        return (0, 0, 0)

    def first(self):
        return None


class _EmptyReportSession:
    def query(self, *args, **kwargs):
        return _EmptyReportQuery()


def test_report_summary_marks_a_valid_empty_period() -> None:
    summary = ReportService(_EmptyReportSession()).summary(
        SimpleNamespace(store_id=uuid4()), date(2026, 1, 1), date(2026, 1, 2)
    )

    assert summary.has_report_data is False
    assert summary.profit_and_loss.sales_total == 0


def test_report_summary_rejects_reversed_dates_with_safe_message() -> None:
    with pytest.raises(HTTPException) as error:
        ReportService(_EmptyReportSession()).summary(
            SimpleNamespace(store_id=uuid4()), date(2026, 1, 3), date(2026, 1, 2), "report-invalid-range"
        )

    assert error.value.status_code == 422
    assert error.value.detail == {
        "message": "End date cannot be earlier than Start date.",
        "code": "invalid_date_range",
        "request_id": "report-invalid-range",
    }


def test_report_calculation_failure_is_logged_and_safely_classified(monkeypatch, caplog) -> None:
    def fail_summary(*args, **kwargs):
        raise OperationalError("SELECT internal_query", {"secret": "do-not-return"}, RuntimeError("database unavailable"))

    monkeypatch.setattr(reports_route.ReportService, "summary", fail_summary)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(store_id=uuid4())
    app.dependency_overrides[get_db] = lambda: _EmptyReportSession()
    try:
        with caplog.at_level(logging.ERROR):
            response = TestClient(app, raise_server_exceptions=False).get(
                "/api/v1/reports/summary?start_date=2026-01-01&end_date=2026-01-02",
                headers={"X-Request-ID": "report-calculation-test"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.headers["X-Request-ID"] == "report-calculation-test"
    assert response.json() == {
        "detail": {
            "message": "Unable to generate the report right now. Please try again.",
            "code": "report_calculation_failed",
            "request_id": "report-calculation-test",
        }
    }
    assert "reports_summary_failed request_id=report-calculation-test exception_type=OperationalError" in caplog.text
    assert "internal_query" not in response.text
    assert "do-not-return" not in response.text
