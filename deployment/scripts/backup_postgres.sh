#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
DATABASE_URL="${DATABASE_URL:-postgresql://inventory_user:inventory123@localhost:5432/inventory_db}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"
pg_dump "$DATABASE_URL" --format=custom --file="$BACKUP_DIR/rainbow_inventory_$TIMESTAMP.dump"
find "$BACKUP_DIR" -name "rainbow_inventory_*.dump" -mtime +30 -delete
