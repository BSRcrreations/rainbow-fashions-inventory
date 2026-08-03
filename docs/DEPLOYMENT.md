# Deployment

Rainbow Fashions uses one FastAPI backend, one React web frontend, one Expo
Android scaffold, and one PostgreSQL database.

## Protected environment configuration

Create the real backend environment file only on the deployment host from
`backend/.env.docker.example`. Keep it outside the repository and release
directories, restrict it to the service owner (`chmod 600`), and provide it to
Compose through the approved host-level configuration path.

The examples intentionally contain `CHANGE_ME` placeholders. Never commit real
passwords, JWT material, database URLs, hostnames, tokens, or private keys.
Before release, run:

```bash
bash scripts/security/check_tracked_secrets.sh
```

## Local Docker

For a local-only environment, copy the reviewed example to the ignored backend
environment path, set values locally, and then run:

```bash
docker compose up --build
```

## HTTPS and backups

Use `deployment/nginx/rainbow-fashions.conf` with an approved TLS terminator.
Run backup and restore scripts only with `DATABASE_URL` sourced from the
protected host environment; do not paste credentials into command history or
documentation.

## GitLab CI/CD

The `shop-inventory` branch is deployed in manual phases through GitLab CI.
See `docs/CI_CD.md` for required variables, server layout, and release steps.
