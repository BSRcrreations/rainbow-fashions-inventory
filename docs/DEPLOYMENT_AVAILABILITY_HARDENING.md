# Deployment Availability Hardening

Target production host: `178.238.237.182`

Application root: `/opt/rainbow-fashions`

Public hostname: `test.rainbow-fashions.in`

## What Publishes Public Traffic

Host-level Nginx is the only public HTTP/HTTPS entry point. Docker Compose binds the frontend container to `127.0.0.1:8080:80`; PostgreSQL and FastAPI are not published.

Expected sockets:

```bash
ss -lntp
```

- Nginx: `0.0.0.0:80`, `0.0.0.0:443`
- Docker frontend: `127.0.0.1:8080`
- PostgreSQL: no public `5432`
- FastAPI: no public `8000`

## Systemd

Install the application service:

```bash
sudo cp deployment/systemd/rainbow-fashions.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rainbow-fashions.service
sudo systemctl start rainbow-fashions.service
sudo systemctl status rainbow-fashions.service
```

Verify boot availability:

```bash
systemctl is-enabled docker
systemctl is-enabled rainbow-fashions
systemctl is-active docker
systemctl is-active rainbow-fashions
```

Install the watchdog:

```bash
sudo cp deployment/systemd/rainbow-health-watch.service /etc/systemd/system/
sudo cp deployment/systemd/rainbow-health-watch.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rainbow-health-watch.timer
sudo systemctl list-timers rainbow-health-watch.timer
```

## Nginx And TLS

```bash
sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx
deployment/scripts/diagnose_domain.sh
dig +short test.rainbow-fashions.in
```

DNS must return:

```text
178.238.237.182
```

If `diagnose_domain.sh` reports `NO_NAMESERVER_DELEGATION`, the domain owner must configure authoritative nameservers at the registrar first. Code, GitLab, Nginx, and Certbot cannot create registrar-level delegation. After delegation exists, add:

```text
Type: A
Name: test
Value: 178.238.237.182
TTL: 300 or Auto
```

Do not run Certbot until `diagnose_domain.sh` reports `DNS_OK`.

Install the virtual host:

```bash
sudo cp deployment/nginx/test.rainbow-fashions.in.conf /etc/nginx/sites-available/test.rainbow-fashions.in
sudo ln -sfn /etc/nginx/sites-available/test.rainbow-fashions.in /etc/nginx/sites-enabled/test.rainbow-fashions.in
sudo nginx -t
sudo systemctl enable --now nginx
```

Obtain and verify TLS:

```bash
sudo certbot --nginx -d test.rainbow-fashions.in
systemctl status certbot.timer
sudo certbot renew --dry-run
```

## Firewall

The helper adds allow rules only; it does not enable UFW.

```bash
sudo deployment/scripts/configure_firewall_ufw.sh
ufw status verbose
```

Required public ports:

- `22/tcp`
- `80/tcp`
- `443/tcp`

## Deployment Verification

Local:

```bash
deployment/scripts/wait_for_application.sh --base-url http://127.0.0.1:8080 --timeout 180
curl -fsS http://127.0.0.1:8080/health/live
curl -fsS http://127.0.0.1:8080/health/ready
```

Public:

```bash
deployment/scripts/wait_for_application.sh --base-url https://test.rainbow-fashions.in --timeout 180
curl -I https://test.rainbow-fashions.in
curl -fsS https://test.rainbow-fashions.in/health/live
curl -fsS https://test.rainbow-fashions.in/health/ready
curl -I http://test.rainbow-fashions.in
```

The HTTP endpoint must redirect to HTTPS with `301` or `308`.

Run full smoke checks:

```bash
LOCAL_BASE_URL=http://127.0.0.1:8080 \
PUBLIC_BASE_URL=https://test.rainbow-fashions.in \
deployment/scripts/smoke_test_production.sh
```

## Rollback

The deployment pipeline records previous and new release paths. If migration, health, local smoke, public smoke, or Nginx verification fails, it restores the previous `current` symlink and restarts the previous application release.

The deployment does not automatically restore a database backup. Migrations must remain backward-compatible with the immediately previous release.

Use expand-and-contract practices:

- Add nullable columns before using them.
- Avoid destructive renames in the same deployment.
- Do not drop columns until a later deployment.

## Alerts

Copy and protect the alert configuration:

```bash
sudo cp deployment/templates/availability-alerts.env.example /opt/rainbow-fashions/shared/availability-alerts.env
sudo chmod 600 /opt/rainbow-fashions/shared/availability-alerts.env
```

Configure `AVAILABILITY_WEBHOOK_URL` only on the server. Do not commit it.

## Validation

Repository:

```bash
cd backend && pytest && alembic heads
cd ../frontend && npm ci && npm run lint && npm run typecheck && npm run test && npm run build
docker compose config
docker compose build
bash -n deployment/scripts/wait_for_application.sh
bash -n deployment/scripts/smoke_test_production.sh
bash -n deployment/scripts/check_application_health.sh
```

Optional when available:

```bash
shellcheck deployment/scripts/*.sh
systemd-analyze verify deployment/systemd/rainbow-fashions.service deployment/systemd/rainbow-health-watch.service deployment/systemd/rainbow-health-watch.timer
nginx -t
```

Do not reboot the VPS automatically. A reboot test requires explicit approval.
