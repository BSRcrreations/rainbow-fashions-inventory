#!/usr/bin/env bash
set -Eeuo pipefail

echo "This script only adds required allow rules. It does not enable UFW."
echo "Required public ports: 22/tcp, 80/tcp, 443/tcp"

command -v ufw >/dev/null 2>&1 || { echo "ufw is not installed." >&2; exit 1; }

ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw status verbose

cat <<'EOF'

Expected listening sockets after deployment:
- Host Nginx: 0.0.0.0:80 and 0.0.0.0:443
- Docker frontend: 127.0.0.1:8080 only
- PostgreSQL: not published publicly
- FastAPI backend: not published publicly

Validate with:
  ss -lntp

Enable UFW only from an active SSH session after confirming OpenSSH is allowed:
  ufw enable
EOF
