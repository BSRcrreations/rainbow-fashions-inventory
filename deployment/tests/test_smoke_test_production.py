from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "deployment" / "scripts" / "smoke_test_production.sh"


FAKE_CURL = r"""#!/usr/bin/env bash
set -eu
for arg in "$@"; do
  case "$arg" in
    */health/live|*/health/ready)
      exit 22
      ;;
  esac
done
printf '<html></html>'
"""


class SmokeTestProductionTests(unittest.TestCase):
    def test_post_deployment_http_failure_fails_smoke_test(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp)
            curl = bin_dir / "curl"
            curl.write_text(FAKE_CURL, encoding="utf-8")
            curl.chmod(curl.stat().st_mode | stat.S_IXUSR)
            env = os.environ.copy()
            env.update(
                {
                    "PATH": f"{bin_dir}:{env['PATH']}",
                    "LOCAL_BASE_URL": "http://local.test",
                    "PUBLIC_BASE_URL": "https://public.test",
                    "HTTP_BASE_URL": "http://public.test",
                }
            )

            result = subprocess.run(["bash", str(SCRIPT)], cwd=ROOT, env=env, text=True, capture_output=True)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Running local smoke tests", result.stdout)


if __name__ == "__main__":
    unittest.main()
