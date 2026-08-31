from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEST_CONFIG = ROOT / "deployment" / "nginx" / "test.rainbow-fashions.in.conf"
PRODUCTION_CONFIG = ROOT / "deployment" / "nginx" / "rainbow-fashions.in.conf"


def test_test_nginx_configuration_is_isolated_and_proxies_loopback_test_port() -> None:
    config = TEST_CONFIG.read_text(encoding="utf-8")

    assert "test.rainbow-fashions.in" in config
    assert "rainbow-fashions.in www.rainbow-fashions.in" not in config
    assert "listen 80;" in config
    assert "listen 443 ssl http2;" in config
    assert "proxy_pass http://127.0.0.1:8081;" in config
    assert "proxy_pass http://127.0.0.1:8000" not in config


def test_frontend_proxy_exposes_only_the_safe_version_endpoint() -> None:
    config = (ROOT / "frontend" / "nginx.conf").read_text(encoding="utf-8")

    assert "location = /version" in config
    assert "proxy_pass http://backend:8000/version;" in config


def test_production_nginx_configuration_is_isolated_and_proxies_loopback_production_port() -> None:
    config = PRODUCTION_CONFIG.read_text(encoding="utf-8")

    for hostname in ("rainbow-fashions.in", "www.rainbow-fashions.in"):
        assert hostname in config
    assert "test.rainbow-fashions.in" not in config
    assert "proxy_pass http://127.0.0.1:8080;" in config
    assert "proxy_pass http://127.0.0.1:8000" not in config
    assert "proxy_set_header Host $host;" in config
    assert "proxy_set_header X-Real-IP $remote_addr;" in config
    assert "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;" in config
    assert "proxy_set_header X-Forwarded-Proto https;" in config
    assert "client_max_body_size 15m;" in config
    assert "proxy_read_timeout 300s;" in config
    assert "return 301 https://$host$request_uri;" in config
