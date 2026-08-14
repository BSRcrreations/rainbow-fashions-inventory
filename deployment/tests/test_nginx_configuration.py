from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "deployment" / "nginx" / "test.rainbow-fashions.in.conf"


def test_public_nginx_configuration_covers_all_required_hosts_and_proxy_safety() -> None:
    config = CONFIG.read_text(encoding="utf-8")

    for hostname in ("test.rainbow-fashions.in", "rainbow-fashions.in", "www.rainbow-fashions.in"):
        assert hostname in config
    assert "listen 80;" in config
    assert "listen 443 ssl http2;" in config
    assert "proxy_pass http://127.0.0.1:8080;" in config
    assert "proxy_set_header Host $host;" in config
    assert "proxy_set_header X-Real-IP $remote_addr;" in config
    assert "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;" in config
    assert "proxy_set_header X-Forwarded-Proto https;" in config
    assert "client_max_body_size 15m;" in config
    assert "proxy_read_timeout 300s;" in config
    assert "return 301 https://$host$request_uri;" in config
