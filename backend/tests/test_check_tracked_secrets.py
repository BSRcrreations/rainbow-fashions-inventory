from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/security/check_tracked_secrets.sh"


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=True, text=True, capture_output=True)


def _repository_with_allowed_examples(tmp_path: Path) -> Path:
    for relative_path in (
        "backend/.env.example",
        "backend/.env.docker.example",
        "backend/.env.test.example",
        "frontend/.env.example",
        "frontend/.env.test.example",
    ):
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("JWT_SECRET_KEY=CHANGE_ME\n", encoding="utf-8")
    _run(["git", "init", "-q"], tmp_path)
    _run(["git", "add", "."], tmp_path)
    return tmp_path


def test_security_check_accepts_only_placeholder_environment_examples(tmp_path: Path):
    repository = _repository_with_allowed_examples(tmp_path)

    result = subprocess.run([str(SCRIPT)], cwd=repository, text=True, capture_output=True)

    assert result.returncode == 0
    assert "no tracked-secret policy violations" in result.stdout


def test_security_check_rejects_trailing_whitespace_environment_filename(tmp_path: Path):
    repository = _repository_with_allowed_examples(tmp_path)
    unsafe_file = repository / "backend/.env "
    unsafe_file.write_text("JWT_SECRET_KEY=CHANGE_ME\n", encoding="utf-8")
    _run(["git", "add", "backend/.env "], repository)

    result = subprocess.run([str(SCRIPT)], cwd=repository, text=True, capture_output=True)

    assert result.returncode == 1
    assert "trailing whitespace" in result.stderr


def test_security_check_rejects_unapproved_environment_filename(tmp_path: Path):
    repository = _repository_with_allowed_examples(tmp_path)
    unsafe_file = repository / "frontend/.env.local"
    unsafe_file.write_text("VITE_API_BASE_URL=CHANGE_ME\n", encoding="utf-8")
    _run(["git", "add", "frontend/.env.local"], repository)

    result = subprocess.run([str(SCRIPT)], cwd=repository, text=True, capture_output=True)

    assert result.returncode == 1
    assert "not an approved example" in result.stderr


def test_security_check_rejects_sensitive_binary_artifacts(tmp_path: Path):
    repository = _repository_with_allowed_examples(tmp_path)
    for relative_path in (
        "backups/release.tar.gz",
        "backend/app/uploads/invoices/document.pdf",
        "backend/tests/fixtures/invoice.pdf",
        "local.sqlite3",
        "keys/service.p12",
    ):
        path = repository / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("placeholder", encoding="utf-8")
    _run(["git", "add", "."], repository)

    result = subprocess.run([str(SCRIPT)], cwd=repository, text=True, capture_output=True)

    assert result.returncode == 1
    assert "archive artifact is tracked" in result.stderr
    assert "runtime upload artifact is tracked" in result.stderr
    assert "invoice fixture is tracked" in result.stderr
    assert "database dump is tracked" in result.stderr
    assert "private-key-like file is tracked" in result.stderr
