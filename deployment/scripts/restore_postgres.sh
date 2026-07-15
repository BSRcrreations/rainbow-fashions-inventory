#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 /path/to/backup.dump"
  exit 1
fi

DATABASE_URL="${DATABASE_URL:-postgresql://inventory_user:inventory123@localhost:5432/inventory_db}"
pg_restore --clean --if-exists --no-owner --dbname="$DATABASE_URL" "$1"
