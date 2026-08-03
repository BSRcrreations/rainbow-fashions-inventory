#!/usr/bin/env bash
# Compatibility entry point for the isolated restore drill.
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/test_database_restore.sh" "$@"
