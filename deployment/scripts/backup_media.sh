#!/usr/bin/env bash
# Backwards-compatible entry point. New deployments should call backup_uploads.sh.
set -Eeuo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/backup_uploads.sh" "$@"
