#!/usr/bin/env bash
set -Eeuo pipefail

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_test_env.sh"
load_test_environment
assert_testing_database

if [[ "${TEST_ENV_MODE:-docker}" == "docker" ]]; then
  write_docker_test_environment
  # This stops only the isolated Compose project and deliberately keeps its test volumes.
  test_compose down --remove-orphans
else
  stop_pid_file "$TEST_RUNTIME_DIR/backend.pid" "uvicorn app.main:app"
  stop_pid_file "$TEST_RUNTIME_DIR/frontend.pid" "vite --mode test"
fi
