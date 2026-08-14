#!/usr/bin/env bash
# The tracked-secret policy also enforces the repository artifact boundary.
# Keep this entry point explicit in CI so artifact validation cannot be skipped.
set -Eeuo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$script_dir/check_tracked_secrets.sh"
