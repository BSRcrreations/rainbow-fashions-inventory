# GitLab CI/CD

The pipeline deploys the `shop-inventory` branch to:

```text
http://178.238.237.182/
```

## Required GitLab CI variables

Set these in GitLab under **Settings > CI/CD > Variables**:

```text
DEPLOY_HOST=178.238.237.182
DEPLOY_USER=<ssh-user>
DEPLOY_SSH_PRIVATE_KEY=<private-key-with-server-access>
```

Optional variables:

```text
DEPLOY_PORT=22
DEPLOY_PATH=/opt/rainbow-fashions
DEPLOY_URL=http://178.238.237.182
DEPLOY_BRANCH=shop-inventory
```

## Server layout

The deploy jobs expect this layout on the server:

```text
/opt/rainbow-fashions/
  current -> releases/<commit-sha>
  releases/
  backups/
  shared/
    backend.env
```

`shared/backend.env` is optional, but production should use it for secrets and runtime settings. Example:

```text
APP_ENV=production
DEBUG=false
DATABASE_URL=postgresql+psycopg://inventory_user:inventory123@postgres:5432/inventory_db
JWT_SECRET_KEY=<long-random-secret>
CORS_ORIGINS=http://178.238.237.182
OCR_PROVIDER=mock
LOG_LEVEL=INFO
```

## Deployment phases

The `shop-inventory` deployment is intentionally split into manual phases:

1. `deploy_phase_1_upload`: uploads and extracts the release bundle.
2. `deploy_phase_2_backup`: backs up the current PostgreSQL database when an existing release is running.
3. `deploy_phase_3_activate`: points `current` at the new release, runs Alembic migrations, and starts Docker Compose.
4. `deploy_phase_4_verify`: checks the app URL and backend health endpoint.

Validation and Docker build jobs run before deployment, so broken backend tests, frontend lint/typecheck/build, or Compose builds stop the release before it reaches the server.
