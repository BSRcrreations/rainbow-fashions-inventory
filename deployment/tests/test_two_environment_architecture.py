from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_compose_overrides_bind_only_loopback_and_use_different_ports() -> None:
    test_compose = (ROOT / "docker-compose.test.yml").read_text(encoding="utf-8")
    production_compose = (ROOT / "docker-compose.prod.yml").read_text(encoding="utf-8")

    assert "127.0.0.1:8081:80" in test_compose
    assert "127.0.0.1:8080:80" in production_compose
    assert "5432" not in test_compose
    assert "5432" not in production_compose
    assert "8000" not in test_compose
    assert "8000" not in production_compose


def test_common_compose_requires_explicit_environment_paths() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    for name in ("BACKEND_ENV_FILE", "UPLOADS_HOST_PATH", "OPENING_STOCK_IMPORTS_HOST_PATH", "BACKUP_STATUS_HOST_PATH"):
        assert f"${{{name}:?" in compose
    assert "postgres_data:/var/lib/postgresql/data" in compose


def test_ci_keeps_environment_deployments_isolated() -> None:
    ci = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")

    assert "tags: [rainbow-test]" in ci
    assert "tags: [rainbow-production]" in ci
    assert "DEPLOY_PATH=/opt/rainbow-fashions-test" in ci
    assert "DEPLOY_PATH=/opt/rainbow-fashions-prod" in ci
    assert "COMPOSE_PROJECT_NAME=rainbow_test" in ci
    assert "COMPOSE_PROJECT_NAME=rainbow_prod" in ci
    assert 'CI_COMMIT_BRANCH == "shop-inventory"' in ci
    assert 'CI_COMMIT_BRANCH == "main"' in ci


def test_deployment_scripts_do_not_probe_release_local_env_files() -> None:
    for script_name in ("backup_before_deploy.sh", "deploy_release.sh"):
        script = (ROOT / "deployment" / "scripts" / script_name).read_text(encoding="utf-8")
        assert "--env-file /dev/null" in script
