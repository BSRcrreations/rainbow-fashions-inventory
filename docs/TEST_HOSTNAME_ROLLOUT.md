# Test hostname and HTTPS rollout

This is a prepared rollout for `https://test.rainbow-fashions.in`. It must not
be applied until the HTTP application and production-environment hardening are
healthy and their deployment pipeline is confirmed successful.

## Target architecture

```text
Internet :443/:80
        |
Host Nginx (TLS and HTTP-to-HTTPS redirect)
        |
127.0.0.1:8080
        |
Docker frontend :80
        |-- /api/     -> Docker backend :8000
        |-- /health   -> Docker backend :8000/health
        |-- /uploads/ -> Docker backend static uploads
        '-- SPA fallback -> React index.html
```

PostgreSQL remains inside Docker and FastAPI remains unexposed to the host
network. Only host Nginx listens publicly on ports 80 and 443.

## Preflight gate

Do not proceed until all of these are true on `178.238.237.182`:

```bash
cd /opt/rainbow-fashions/current
docker compose ps
curl -fsS http://127.0.0.1/health
curl -I http://127.0.0.1/
```

The PostgreSQL, backend, and frontend containers must be healthy. Confirm that
the production environment is loaded with `APP_ENV=production` and
`DEBUG=false` without printing secret values.

## DNS

Create this DNS A record before requesting a certificate:

```text
test  A  178.238.237.182
```

Wait for DNS propagation and confirm it resolves to the server from an
external network.

## Configuration prepared in this repository

1. Docker Compose binds the frontend container's port 80 only to
   `127.0.0.1:8080`. It is no longer publicly exposed directly.
2. The frontend Nginx proxy now forwards `/uploads/` to the backend so product,
   brand, and invoice uploads remain reachable through the hostname.
3. `deployment/nginx/test.rainbow-fashions.in.conf` is the final host-level
   Nginx virtual host. It redirects HTTP to HTTPS and proxies every path to the
   loopback-only frontend, preserving `/api/`, `/health`, uploads, and React
   SPA fallback.

Before restarting Docker on the server, set this exact non-secret production
setting in `/opt/rainbow-fashions/shared/backend.env`:

```text
CORS_ORIGINS=https://test.rainbow-fashions.in
```

Do not print, copy into Git, or change unrelated values from that file.

## Host Nginx and LetsEncrypt rollout

1. Install Nginx and Certbot on the host. Ensure inbound TCP 80 and 443 are
   allowed by the server firewall.
2. Copy `deployment/nginx/test.rainbow-fashions.in.conf` to
   `/etc/nginx/sites-available/test.rainbow-fashions.in` and create the
   `sites-enabled` symlink. Create the ACME webroot:

   ```bash
   sudo mkdir -p /var/www/certbot
   ```

3. Because the final configuration references the certificate files, initially
   enable only its port-80 server block, run `sudo nginx -t`, and reload Nginx.
4. Request the certificate with the webroot challenge:

   ```bash
   sudo certbot certonly --webroot -w /var/www/certbot -d test.rainbow-fashions.in
   ```

5. Enable the complete HTTPS server block, run `sudo nginx -t`, and reload
   Nginx. Then apply the Compose change so the frontend moves from public
   `:80` to loopback-only `127.0.0.1:8080`.

Use a Cloudflare Origin certificate only when Cloudflare proxies the hostname
and SSL/TLS mode is **Full (strict)**. For a direct public DNS A record, use
LetsEncrypt as shown above.

## Verification and renewal

Run these from a client outside the server:

```bash
curl -I http://test.rainbow-fashions.in
curl -I https://test.rainbow-fashions.in
curl -fsS https://test.rainbow-fashions.in/health
```

The HTTP response must redirect to HTTPS, the HTTPS response must succeed, and
the health endpoint must return successfully. Also verify a normal SPA route,
an `/api/` request, and an existing `/uploads/products/...` URL.

Validate automatic LetsEncrypt renewal without changing a certificate:

```bash
sudo certbot renew --dry-run
```

Do not add a restrictive Content-Security-Policy until the React build and all
upload flows have been tested; the included security headers are compatible
with the current application and upload proxy.
