#!/usr/bin/env bash
# Report paths containing fixed bcrypt/Argon2 hashes outside test-only sources.
set -u -o pipefail

repo_root=$(git rev-parse --show-toplevel) || exit 2
cd "$repo_root" || exit 2

failed=0
while IFS= read -r path; do
  case "$path" in
    backend/tests/*|frontend/src/**/*.test.*|scripts/security/check_fixed_password_hashes.sh)
      continue
      ;;
  esac
  printf 'security check: fixed password hash outside test source: %s\n' "$path" >&2
  failed=1
done < <(git grep -IlE '\$2[aby]\$[0-9]{2}\$[./A-Za-z0-9]{20,}|\$argon2(id|i|d)\$' || true)

exit "$failed"
