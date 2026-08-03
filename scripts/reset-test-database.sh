#!/usr/bin/env bash
set -Eeuo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_test_env.sh"
load_test_environment
assert_testing_database
require_testing_password

database_name="$(database_name_from_url "$DATABASE_URL")"
confirm_test_reset "$database_name"

if [[ "${TEST_ENV_MODE:-docker}" == "docker" ]]; then
  write_docker_test_environment
  test_compose up -d rainbow-test-db
  printf 'Recreating schema in isolated Docker database %s only.\n' "$database_name"
  test_compose exec -T rainbow-test-db sh -lc 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"'
  test_compose run --rm rainbow-test-backend python scripts/bootstrap_test_database.py
  test_compose run --rm rainbow-test-backend alembic upgrade head
  test_compose run --rm rainbow-test-backend sh -lc 'alembic current && test "$(alembic heads | grep -c "(head)")" -eq 1'
  test_compose run --rm rainbow-test-backend python scripts/seed_test_data.py
else
  command -v psql >/dev/null 2>&1 || { printf 'psql is required to reset the isolated test database.\n' >&2; exit 2; }
  command -v createdb >/dev/null 2>&1 || { printf 'createdb is required to create the isolated test database.\n' >&2; exit 2; }
  database_cli_url="$(postgres_cli_url "$DATABASE_URL")"
  admin_cli_url="${database_cli_url%/*}/postgres"
  if ! psql "$database_cli_url" -tAc 'SELECT 1' >/dev/null 2>&1; then
    printf 'Creating isolated test database %s.\n' "$database_name"
    createdb --maintenance-db="$admin_cli_url" "$database_name"
  fi
  printf 'Recreating schema in %s only.\n' "$database_name"
  psql "$database_cli_url" -v ON_ERROR_STOP=1 -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
  (cd "$PROJECT_ROOT/backend" && python scripts/bootstrap_test_database.py)
  (cd "$PROJECT_ROOT/backend" && alembic upgrade head)
  (cd "$PROJECT_ROOT/backend" && alembic current && test "$(alembic heads | grep -c '(head)')" -eq 1)
  "$PROJECT_ROOT/scripts/seed-test-data.sh"
fi
