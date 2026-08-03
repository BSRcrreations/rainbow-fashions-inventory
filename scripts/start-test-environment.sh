#!/usr/bin/env bash
set -Eeuo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_test_env.sh"
load_test_environment
assert_testing_database

mode="${TEST_ENV_MODE:-docker}"
case "$mode" in
  docker)
    command -v docker >/dev/null 2>&1 || { printf 'Docker is required for TEST_ENV_MODE=docker.\n' >&2; exit 2; }
    write_docker_test_environment
    test_compose build rainbow-test-backend rainbow-test-frontend
    test_compose up -d rainbow-test-db
    printf 'Waiting for isolated UAT database readiness...\n'
    for _ in $(seq 1 30); do
      if test_compose exec -T rainbow-test-db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
        break
      fi
      sleep 2
    done
    test_compose exec -T rainbow-test-db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null
    test_compose run --rm --no-deps rainbow-test-backend python scripts/bootstrap_test_database.py
    test_compose run --rm --no-deps rainbow-test-backend alembic upgrade heads
    test_compose run --rm --no-deps rainbow-test-backend python scripts/seed_test_data.py
    test_compose up -d rainbow-test-backend rainbow-test-frontend
    printf 'Waiting for isolated UAT readiness at http://127.0.0.1:8001/health/ready ...\n'
    for _ in $(seq 1 30); do
      if curl -fsS http://127.0.0.1:8001/health/ready >/dev/null; then
        printf 'UAT backend:  http://127.0.0.1:8001\nUAT frontend: http://127.0.0.1:5174\n'
        exit 0
      fi
      sleep 2
    done
    test_compose ps >&2
    printf 'UAT backend did not become ready.\n' >&2
    exit 1
    ;;
  direct)
    require_testing_password
    mkdir -p "$TEST_RUNTIME_DIR"
    [[ -x "$PROJECT_ROOT/backend/.venv/bin/python" ]] || { printf 'Missing backend/.venv/bin/python.\n' >&2; exit 2; }
    (cd "$PROJECT_ROOT/backend" && env APP_ENV=testing .venv/bin/python scripts/bootstrap_test_database.py)
    (cd "$PROJECT_ROOT/backend" && env APP_ENV=testing .venv/bin/alembic upgrade heads)
    (cd "$PROJECT_ROOT/backend" && env APP_ENV=testing .venv/bin/python scripts/seed_test_data.py)
    if [[ ! -f "$TEST_RUNTIME_DIR/backend.pid" ]]; then
      (cd "$PROJECT_ROOT/backend" && nohup env APP_ENV=testing .venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001 > "$TEST_RUNTIME_DIR/backend.log" 2>&1 & echo $! > "$TEST_RUNTIME_DIR/backend.pid")
    fi
    if [[ ! -f "$TEST_RUNTIME_DIR/frontend.pid" ]]; then
      (cd "$PROJECT_ROOT/frontend" && nohup npm run dev:test > "$TEST_RUNTIME_DIR/frontend.log" 2>&1 & echo $! > "$TEST_RUNTIME_DIR/frontend.pid")
    fi
    printf 'Direct UAT processes started. Backend: http://127.0.0.1:8001, frontend: http://127.0.0.1:5174\n'
    ;;
  *) printf 'TEST_ENV_MODE must be docker or direct.\n' >&2; exit 2 ;;
esac
