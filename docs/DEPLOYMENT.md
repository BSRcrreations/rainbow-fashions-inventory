# Deployment

Rainbow Fashions uses one FastAPI backend, one React web frontend, one Expo Android app, and one PostgreSQL database.

## Local Docker

```bash
docker compose up --build
```

Open:

```text
http://localhost
```

## Services

- `postgres`: PostgreSQL database with schema and seed initialization.
- `backend`: FastAPI REST API serving web and Android clients.
- `frontend`: Nginx-served React build.

## HTTPS

Use the reverse proxy config in:

```text
deployment/nginx/rainbow-fashions.conf
```

In production, place TLS termination in Nginx using Certbot or a managed load balancer.

For the hardened `test.rainbow-fashions.in` deployment, use:

```text
docs/DEPLOYMENT_AVAILABILITY_HARDENING.md
deployment/nginx/test.rainbow-fashions.in.conf
deployment/systemd/rainbow-fashions.service
deployment/systemd/rainbow-health-watch.timer
```

## Backups

Create backup:

```bash
DATABASE_URL=postgresql://inventory_user:inventory123@localhost:5432/inventory_db \
deployment/scripts/backup_postgres.sh
```

Restore backup:

```bash
DATABASE_URL=postgresql://inventory_user:inventory123@localhost:5432/inventory_db \
deployment/scripts/restore_postgres.sh ./backups/rainbow_inventory_YYYYMMDD_HHMMSS.dump
```

Backups older than 30 days are removed by the backup script.

## GitLab CI/CD

The `shop-inventory` branch is deployed in manual phases through GitLab CI.
See `docs/CI_CD.md` for required variables, server layout, and release steps.
