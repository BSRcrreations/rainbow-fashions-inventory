#!/usr/bin/env bash
# Report tracked-secret policy violations by path only. Never print matched values.
set -u -o pipefail

repo_root=$(git rev-parse --show-toplevel) || exit 2
cd "$repo_root" || exit 2

failed=0
case_conflicts=$(mktemp "${TMPDIR:-/tmp}/rainbow-env-paths.XXXXXX")
trap 'rm -f "$case_conflicts"' EXIT

report() {
  printf 'security check: %s\n' "$1" >&2
  failed=1
}

is_approved_example() {
  case "$1" in
    backend/.env.example|backend/.env.docker.example|backend/.env.test.example|frontend/.env.example|frontend/.env.test.example)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

is_environment_filename() {
  case "$1" in
    .env*|*/.env*|*.env|*.env.*) return 0 ;;
    *) return 1 ;;
  esac
}

while IFS= read -r -d '' path; do
  if [[ "$path" =~ ^[[:space:]] || "$path" =~ [[:space:]]$ ]]; then
    report "filename contains leading or trailing whitespace: $path"
  fi
  if [[ "$path" =~ [[:cntrl:]] ]]; then
    report "filename contains a control character: $path"
  fi

  if is_environment_filename "$path"; then
    if ! is_approved_example "$path"; then
      report "tracked environment file is not an approved example: $path"
    fi
    printf '%s\n' "$path" | tr '[:upper:]' '[:lower:]' >> "$case_conflicts"
  fi

  case "$path" in
    *.pem|*.key|*.p12|*.pfx)
      report "private-key-like file is tracked: $path"
      ;;
    *.dump|*.backup|*.bak|*.sql.gz)
      report "database dump is tracked: $path"
      ;;
  esac
done < <(git ls-files -z)

while IFS= read -r duplicate; do
  [ -z "$duplicate" ] || report "case-conflicting environment filename: $duplicate"
done < <(LC_ALL=C sort "$case_conflicts" | uniq -d)

for example in \
  backend/.env.example \
  backend/.env.docker.example \
  backend/.env.test.example \
  frontend/.env.example \
  frontend/.env.test.example; do
  if ! git ls-files --error-unmatch "$example" >/dev/null 2>&1; then
    report "approved environment example is missing: $example"
    continue
  fi

  if grep -E '^[[:space:]]*(POSTGRES_PASSWORD|OWNER_PASSWORD|UAT_TEST_PASSWORD|JWT_SECRET_KEY|DELETE_AUTH_PASSWORD_HASH|VITE_API_BASE_URL)=' "$example" | grep -Ev '^[[:space:]]*(POSTGRES_PASSWORD|OWNER_PASSWORD|UAT_TEST_PASSWORD|JWT_SECRET_KEY|DELETE_AUTH_PASSWORD_HASH|VITE_API_BASE_URL)=CHANGE_ME[[:space:]]*$' >/dev/null; then
    report "approved example contains a non-placeholder sensitive value: $example"
  fi
  if git grep -q -E '^DATABASE_URL=.*(postgres|mysql|mongodb).*' -- "$example" 2>/dev/null && ! git grep -q -E '^DATABASE_URL=.*CHANGE_ME:CHANGE_ME.*' -- "$example" 2>/dev/null; then
    report "database connection example contains a reusable password: $example"
  fi
done

while IFS= read -r path; do
  [ -z "$path" ] || report "private key material is tracked: $path"
done < <(git grep -Il -e '-----BEGIN [A-Z ]*PRIVATE KEY-----' || true)

while IFS= read -r path; do
  case "$path" in
    backend/tests/*|frontend/src/**/*.test.*|frontend/src/api/client.ts|scripts/security/check_tracked_secrets.sh)
      continue
      ;;
  esac
  [ -z "$path" ] || report "possible fixed credential assignment: $path"
done < <(git grep -IlE "(PASSWORD|SECRET|TOKEN|JWT)[A-Za-z0-9_]*[[:space:]]*[:=][[:space:]]*['\"][A-Za-z0-9][^'\"]{7,}['\"]" || true)

if [ "$failed" -ne 0 ]; then
  exit 1
fi

printf 'security check: no tracked-secret policy violations found\n'
