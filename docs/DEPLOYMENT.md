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
1. Create a protected environment file from a reviewed template and set owner
   read/write permissions.
2. Start PostgreSQL and apply Alembic migrations.
3. Provision the first owner only with the approved bootstrap command; this
   base requires the pending security-bootstrap merge before that step.
4. Start backend and frontend, then verify liveness/readiness endpoints.
5. Verify backup creation and a non-production restore test before release.

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

### One-time production runner Nginx permission

The Docker frontend binds only to `127.0.0.1:8080`; host Nginx owns public
ports 80 and 443. During the first migration from the legacy Docker port-80
binding, Nginx can be inactive before deployment because Docker still owns
port 80. The activation job starts Nginx only after Compose releases that
port. As root on the server, install the narrowly scoped rule:

```bash
visudo -cf /opt/rainbow-fashions/current/deployment/templates/gitlab-runner-nginx.sudoers
install -o root -g root -m 440 /opt/rainbow-fashions/current/deployment/templates/gitlab-runner-nginx.sudoers /etc/sudoers.d/gitlab-runner-rainbow-nginx
sudo -u gitlab-runner sudo -n /usr/bin/systemctl is-active nginx || true
```

Do not grant the runner unrestricted sudo access. Once the deployment has
recreated the frontend, verify `systemctl is-active nginx` reports `active`.
Terminate TLS with Certbot, a managed load balancer, or an equivalent approved
service.

For the hardened `test.rainbow-fashions.in` deployment, use:

```text
docs/DEPLOYMENT_AVAILABILITY_HARDENING.md
deployment/nginx/test.rainbow-fashions.in.conf
deployment/systemd/rainbow-fashions.service
deployment/systemd/rainbow-health-watch.timer
```

## Backups

Set `DATABASE_URL` in the protected deployment environment before running the
backup or restore scripts. Never place credentials directly in shell history,
documentation, or Git.

## GitLab CI/CD

The `shop-inventory` branch is deployed in manual phases through GitLab CI.
See `docs/CI_CD.md` for required variables, server layout, and release steps.

Backup and restore scripts live under `deployment/scripts/`; their operational
status requires live verification and must not be inferred from source alone.
