from __future__ import annotations

import subprocess
from pathlib import Path

from app.core.security import hash_password


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/security/check_fixed_password_hashes.sh"


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=True, text=True, capture_output=True)


def _initialize_repository(tmp_path: Path) -> Path:
    _run(["git", "init", "-q"], tmp_path)
    return tmp_path


def test_fixed_hash_scan_allows_runtime_test_hashes(tmp_path: Path):
    repository = _initialize_repository(tmp_path)
    test_path = repository / "backend/tests/test_passwords.py"
    test_path.parent.mkdir(parents=True)
    test_path.write_text(f"HASH = {hash_password('test-' + __import__('uuid').uuid4().hex)!r}\n", encoding="utf-8")
    _run(["git", "add", "."], repository)

    result = subprocess.run([str(SCRIPT)], cwd=repository, text=True, capture_output=True)

    assert result.returncode == 0


def test_fixed_hash_scan_rejects_non_test_source(tmp_path: Path):
    repository = _initialize_repository(tmp_path)
    source_path = repository / "backend/app/example.py"
    source_path.parent.mkdir(parents=True)
    source_path.write_text(f"HASH = {hash_password('test-' + __import__('uuid').uuid4().hex)!r}\n", encoding="utf-8")
    _run(["git", "add", "."], repository)

    result = subprocess.run([str(SCRIPT)], cwd=repository, text=True, capture_output=True)

    assert result.returncode == 1
    assert "fixed password hash outside test source" in result.stderr
