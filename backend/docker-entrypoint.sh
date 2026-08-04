#!/usr/bin/env sh
set -eu

# Alembic is the only supported schema initializer. A failed migration prevents
# the API from starting; no downgrade and no seed data are attempted here.
if [ "${RUN_MIGRATIONS_ON_STARTUP:-true}" = "true" ]; then
  echo "Applying database migrations to Alembic head..."
  alembic upgrade head
  echo "Database migrations completed."
fi

exec "$@"
