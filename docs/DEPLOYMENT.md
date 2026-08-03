# Deployment

Rainbow Fashions uses one FastAPI backend, one React web frontend, one Expo
Android scaffold, and one PostgreSQL database.

## Local Docker

Create a local backend environment file from the reviewed example, set real
values only on the deployment host, and keep it out of Git:

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
