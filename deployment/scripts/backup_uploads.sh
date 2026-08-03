#!/usr/bin/env bash
# Compatibility entry point retained for installed service units.
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/prepare_upload_backup.sh" "$@"
