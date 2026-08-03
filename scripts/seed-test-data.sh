#!/usr/bin/env bash
set -Eeuo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_test_env.sh"
load_test_environment
assert_testing_database
require_testing_password

printf 'Seeding deterministic UAT catalog and users into %s.\n' "$(database_name_from_url "$DATABASE_URL")"
if [[ "${TEST_ENV_MODE:-docker}" == "docker" ]]; then
  write_docker_test_environment
  test_compose up -d rainbow-test-db rainbow-test-backend
  test_compose exec -T rainbow-test-backend python scripts/seed_test_data.py
else
  (cd "$PROJECT_ROOT/backend" && .venv/bin/python scripts/seed_test_data.py)
fi
