# GitLab CI/CD

The pipeline deploys the `shop-inventory` branch to:

```text
http://178.238.237.182/
```

## GitLab CI variables

The production runner runs on the deployment server, so no SSH deploy variables are required.
Optional overrides can be set in GitLab under **Settings > CI/CD > Variables**:

```text
DEPLOY_PATH=/opt/rainbow-fashions
DEPLOY_URL=http://178.238.237.182
DEPLOY_BRANCH=shop-inventory
```

## Server layout

The deploy jobs create and use this layout on the server:

```text
/opt/rainbow-fashions/
  current -> releases/<commit-sha>
  releases/
  backups/
  shared/
    backend.env
```

`shared/backend.env` is required for production secrets and runtime settings.
Create it at `/opt/rainbow-fashions/shared/backend.env` from the safe template
at `deployment/templates/backend.production.template`. Never commit the
real file. See `deployment/templates/README.md` for the required secret
generation commands, permissions, and validation rules.

## Deployment phases

The `shop-inventory` deployment runs automatically after validation passes:

1. `deploy_phase_1_upload`: uploads and extracts the release bundle.
2. `deploy_phase_2_backup`: backs up the current PostgreSQL database when an existing release is running.
3. `deploy_phase_3_activate`: points `current` at the new release, runs Alembic migrations, and starts Docker Compose.
4. `deploy_phase_4_verify`: checks the app URL and backend health endpoint.

Validation and Docker build jobs run before deployment, so broken backend tests, frontend lint/typecheck/build, or Compose builds stop the release before it reaches the server.
