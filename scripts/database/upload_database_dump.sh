#!/usr/bin/env bash
set -Eeuo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_common.sh"
load_database_migration_config
umask 077

usage() {
  printf 'Usage: %s /absolute/path/to/local.dump\n' "$(basename "$0")" >&2
  exit 2
}

[[ $# -eq 1 ]] || usage
dump_file="$1"
[[ -f "$dump_file" && -s "$dump_file" ]] || { printf 'Dump file does not exist or is empty.\n' >&2; exit 2; }
require_command pg_restore
pg_restore -l "$dump_file" >/dev/null
require_remote_connection
require_value REMOTE_STAGING_DIR

checksum="$(file_checksum "$dump_file")"
base_name="$(basename "$dump_file")"
remote_ssh "mkdir -p -- '$REMOTE_STAGING_DIR' && umask 077 && test -d '$REMOTE_STAGING_DIR'"
remote_scp "$dump_file" "$REMOTE_SSH_USER@$REMOTE_SSH_HOST:$REMOTE_STAGING_DIR/$base_name"
if [[ -f "$dump_file.sha256" ]]; then
  remote_scp "$dump_file.sha256" "$REMOTE_SSH_USER@$REMOTE_SSH_HOST:$REMOTE_STAGING_DIR/$base_name.sha256"
fi
if [[ -f "$dump_file.manifest" ]]; then
  remote_scp "$dump_file.manifest" "$REMOTE_SSH_USER@$REMOTE_SSH_HOST:$REMOTE_STAGING_DIR/$base_name.manifest"
fi

remote_checksum="$(remote_ssh bash -s -- "$REMOTE_STAGING_DIR/$base_name" <<'REMOTE'
set -Eeuo pipefail
file="$1"
test -s "$file"
if command -v sha256sum >/dev/null 2>&1; then
  sha256sum "$file" | awk '{print $1}'
else
  shasum -a 256 "$file" | awk '{print $1}'
fi
REMOTE
)"
[[ "$checksum" == "$remote_checksum" ]] || { printf 'Remote checksum mismatch; the staged dump must not be imported.\n' >&2; exit 1; }
printf 'Upload complete.\nREMOTE_STAGED_DUMP_PATH=%s/%s\nSHA256=%s\n' "$REMOTE_STAGING_DIR" "$base_name" "$checksum"
