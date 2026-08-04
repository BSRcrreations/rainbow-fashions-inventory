from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_web_and_mobile_login_fields_start_empty_without_published_credentials():
    web_login = _read("frontend/src/pages/LoginPage.tsx")
    mobile_login = _read("mobile/App.tsx")

    assert 'const [email, setEmail] = useState("");' in web_login
    assert 'const [password, setPassword] = useState("");' in web_login
    assert 'autoComplete="username"' in web_login
    assert 'autoComplete="current-password"' in web_login
    assert 'const [email, setEmail] = useState("");' in mobile_login
    assert 'const [password, setPassword] = useState("");' in mobile_login


def test_seed_and_default_compose_startup_do_not_create_login_credentials():
    seed = _read("database/seed.sql")
    compose = _read("docker-compose.yml")

    assert "INSERT INTO users" not in seed
    assert "password_hash" not in seed
    assert "seed.sql" not in compose


def test_installation_uses_bootstrap_not_published_login_details():
    installation = _read("docs/INSTALLATION.md")

    assert "bootstrap_owner.py" in installation
    assert "OWNER_EMAIL=CHANGE_ME" in installation
    assert "OWNER_PASSWORD=CHANGE_ME" in installation
    assert "Default login" not in installation
