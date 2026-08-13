# Deployment environment templates

The real environment files are server-only, mode `0600`, and are never copied
into a release, artifact, or Git. Use the reviewed placeholder templates only
to create them manually:

| Environment | Template | Server-only path |
| --- | --- | --- |
| Test | `backend.test.template` | `/opt/rainbow-fashions-test/shared/backend.env` |
| Production | `backend.production.template` | `/opt/rainbow-fashions-prod/shared/backend.env` |

Generate separate strong database passwords and JWT signing secrets for each
environment. The test file must use `APP_ENV=staging` or `test`, while the
production file must use `APP_ENV=production`; both require `DEBUG=false`.
Set only the corresponding HTTPS origin(s) in `CORS_ORIGINS`.

Do not source these files in a terminal with shell tracing enabled. The CI
preflight checks names, permissions, safe policy constraints, and environment
identity without printing values.
