from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "deployment" / "scripts" / "diagnose_domain.sh"


FAKE_DIG = r"""#!/usr/bin/env bash
set -eu
scenario="${DNS_SCENARIO:-ok}"
args="$*"

if [[ "$args" == *"+trace"* ]]; then
  echo "trace for test.rainbow-fashions.in"
  exit 0
fi

record=""
resolver="system"
for arg in "$@"; do
  case "$arg" in
    @1.1.1.1) resolver="1111" ;;
    @8.8.8.8) resolver="8888" ;;
    NS|SOA|A|AAAA|CNAME) record="$arg" ;;
  esac
done

case "$record" in
  NS)
    [[ "$scenario" == "missing_ns" ]] && exit 0
    [[ "$scenario" == "ns_mismatch" ]] && { echo "wrong.example.net."; exit 0; }
    echo "abby.ns.cloudflare.com."
    echo "walt.ns.cloudflare.com."
    ;;
  SOA)
    [[ "$scenario" == "missing_ns" ]] && exit 0
    echo "abby.ns.cloudflare.com. dns.cloudflare.com. 1 10000 2400 604800 300"
    ;;
  A)
    [[ "$scenario" == "missing_a" ]] && exit 0
    if [[ "$scenario" == "wrong_a" ]]; then echo "203.0.113.5"; exit 0; fi
    if [[ "$scenario" == "resolver_disagreement" && "$resolver" == "8888" ]]; then echo "203.0.113.5"; exit 0; fi
    echo "178.238.237.182"
    ;;
  AAAA)
    [[ "$scenario" == "unexpected_ipv6" ]] && echo "2001:db8::1"
    ;;
  CNAME)
    ;;
esac
"""


FAKE_CURL = r"""#!/usr/bin/env bash
set -eu
scenario="${DNS_SCENARIO:-ok}"
args="$*"
if [[ "$args" == *"rdap.org/domain"* ]]; then
  case "$scenario" in
    unregistered) echo '{"errorCode":404,"title":"DOMAIN NOT FOUND"}' ;;
    on_hold) echo '{"ldhName":"rainbow-fashions.in","status":["clientHold"],"entities":[{"roles":["registrar"],"vcardArray":["vcard",[["fn",{},"text","Example Registrar"]]]}]}' ;;
    *) echo '{"ldhName":"rainbow-fashions.in","status":["active"],"entities":[{"roles":["registrar"],"vcardArray":["vcard",[["fn",{},"text","Example Registrar"]]]}]}' ;;
  esac
  exit 0
fi
if [[ "$args" == *"http://test.rainbow-fashions.in"* ]]; then
  [[ "$scenario" == "http_refused" ]] && { echo "000"; exit 0; }
  echo "200"
  exit 0
fi
echo "200"
"""


FAKE_WHOIS = r"""#!/usr/bin/env bash
set -eu
scenario="${DNS_SCENARIO:-ok}"
if [[ "$scenario" == "unregistered" ]]; then
  echo "No match for domain"
else
  echo "Registrar: Example Registrar"
  if [[ "$scenario" == "on_hold" ]]; then
    echo "Domain Status: clientHold"
  else
    echo "Domain Status: active"
  fi
  echo "Registrant Email: owner-secret@example.test"
fi
"""


class DiagnoseDomainTests(unittest.TestCase):
    def run_scenario(self, scenario: str, extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmp:
            bin_dir = Path(tmp)
            for name, body in {"dig": FAKE_DIG, "curl": FAKE_CURL, "whois": FAKE_WHOIS}.items():
                target = bin_dir / name
                target.write_text(body)
                target.chmod(target.stat().st_mode | stat.S_IXUSR)
            env = os.environ.copy()
            env.update({
                "PATH": f"{bin_dir}:{env['PATH']}",
                "DNS_SCENARIO": scenario,
                "EXPECTED_NAMESERVERS": "abby.ns.cloudflare.com,walt.ns.cloudflare.com",
            })
            if extra_env:
                env.update(extra_env)
            return subprocess.run(["bash", str(SCRIPT)], text=True, capture_output=True, env=env, cwd=ROOT)

    def assert_state(self, scenario: str, state: str, exit_code: int = 1) -> None:
        result = self.run_scenario(scenario)
        self.assertEqual(result.returncode, exit_code, result.stdout + result.stderr)
        self.assertIn(f"state={state}", result.stdout)

    def test_unregistered_domain(self) -> None:
        self.assert_state("unregistered", "DOMAIN_NOT_REGISTERED")

    def test_missing_ns_delegation(self) -> None:
        result = self.run_scenario("missing_ns")
        self.assertEqual(result.returncode, 1)
        self.assertIn("state=NO_NAMESERVER_DELEGATION", result.stdout)
        self.assertIn("Registrar action required.", result.stdout)

    def test_domain_on_hold(self) -> None:
        self.assert_state("on_hold", "DOMAIN_ON_HOLD")

    def test_missing_a_record(self) -> None:
        self.assert_state("missing_a", "APP_A_RECORD_MISSING")

    def test_wrong_a_record(self) -> None:
        self.assert_state("wrong_a", "APP_A_RECORD_WRONG")

    def test_unexpected_ipv6(self) -> None:
        self.assert_state("unexpected_ipv6", "UNEXPECTED_IPV6")

    def test_resolver_disagreement(self) -> None:
        self.assert_state("resolver_disagreement", "RESOLVER_DISAGREEMENT")

    def test_dns_success_with_http_refused(self) -> None:
        self.assert_state("http_refused", "DNS_OK_HTTP_UNREACHABLE")

    def test_dns_only_success_ignores_http_refusal(self) -> None:
        result = self.run_scenario("http_refused", {"DNS_ONLY": "true"})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("dns_only=true", result.stdout)
        self.assertIn("state=DNS_OK", result.stdout)
        self.assertNotIn("http_port_80_status", result.stdout)

    def test_dns_and_http_success(self) -> None:
        self.assert_state("ok", "DNS_OK", exit_code=0)

    def test_nameserver_mismatch(self) -> None:
        self.assert_state("ns_mismatch", "NAMESERVER_MISMATCH")

    def test_no_credentials_are_printed(self) -> None:
        result = self.run_scenario("ok")
        self.assertNotIn("owner-secret@example.test", result.stdout)
        self.assertNotIn("password", result.stdout.lower())
        self.assertNotIn("token", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
