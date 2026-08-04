from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_has_exactly_one_head() -> None:
    backend = Path(__file__).resolve().parents[1]
    config = Config(str(backend / "alembic.ini"))
    config.set_main_option("script_location", str(backend / "alembic"))
    assert len(ScriptDirectory.from_config(config).get_heads()) == 1


def test_docker_initializes_with_alembic_not_sql_snapshot() -> None:
    root = Path(__file__).resolve().parents[2]
    compose = (root / "docker-compose.yml").read_text(encoding="utf-8")
    dockerfile = (root / "backend" / "Dockerfile").read_text(encoding="utf-8")
    entrypoint = (root / "backend" / "docker-entrypoint.sh").read_text(encoding="utf-8")
    assert "docker-entrypoint-initdb.d" not in compose
    assert "ENTRYPOINT" in dockerfile
    assert "alembic upgrade head" in entrypoint
