#!/usr/bin/env bash
set -Eeuo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_test_env.sh"
load_test_environment
assert_testing_database

(cd "$PROJECT_ROOT/backend" && .venv/bin/python -m pytest -q)
(cd "$PROJECT_ROOT/backend" && test "$(alembic heads | grep -c '(head)')" -eq 1)
(cd "$PROJECT_ROOT/frontend" && npm test -- --run && npm run lint && npm run typecheck && npm run build)
