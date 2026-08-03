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
cp backend/.env.docker.example backend/.env
docker compose up --build
```

Normal Docker startup initializes the schema but does not create an owner or
seed sample business data. Bootstrap the owner through an approved shell on the
host using placeholder-substituted environment variables:

```bash
docker compose exec \
  -e OWNER_EMAIL=CHANGE_ME \
  -e OWNER_PASSWORD=CHANGE_ME \
  backend python scripts/bootstrap_owner.py \
  --store-name "CHANGE_ME" \
  --store-code "CHANGE_ME"
```

Do not commit real secrets, connection strings, passwords, or generated dumps.

## HTTPS

Use the reverse proxy configuration in `deployment/nginx/rainbow-fashions.conf`.
Terminate TLS with Certbot, a managed load balancer, or an equivalent approved
service.

## Backups

Set `DATABASE_URL` in the protected deployment environment before running the
backup or restore scripts. Never place credentials directly in shell history,
documentation, or Git.

## GitLab CI/CD

The `shop-inventory` branch is deployed in manual phases through GitLab CI.
See `docs/CI_CD.md` for required variables, server layout, and release steps.
