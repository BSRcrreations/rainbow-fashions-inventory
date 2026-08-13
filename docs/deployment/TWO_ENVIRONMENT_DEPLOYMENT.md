# Separate test and production deployments

## Architecture

| Property | Test | Production |
| --- | --- | --- |
| Git branch | `shop-inventory` | `main` |
| GitLab environment | `staging` | `production` |
| Public domain | `https://test.rainbow-fashions.in` | `https://rainbow-fashions.in`, `https://www.rainbow-fashions.in` |
| Application root | `/opt/rainbow-fashions-test` | `/opt/rainbow-fashions-prod` |
| Compose project | `rainbow_test` | `rainbow_prod` |
| Frontend loopback binding | `127.0.0.1:8081` | `127.0.0.1:8080` |
| Backend/PostgreSQL host binding | none | none |
| Runner tag | `rainbow-test` | `rainbow-production` |

Both stacks use `docker-compose.yml` plus exactly one environment override.
Docker scopes `postgres_data` by project name, producing distinct volumes:
`rainbow_test_postgres_data` and `rainbow_prod_postgres_data`. Never pass an
external volume name and never run a command for one project from the other
environment's release directory.

Each environment owns its own `releases`, `current` symlink, `shared`,
`backups`, uploads, opening-stock imports, and backup status directories.
The only public listeners are host Nginx ports 80 and 443. Containers bind the
frontends to loopback only; PostgreSQL and FastAPI are not published.

## Server preparation — manual and gated

Perform these actions only with authenticated server access, after recording
the existing containers and PostgreSQL volume. Do not remove, recreate, or
rename the existing data volume until it has been identified as either the
future production volume or intentionally retired under an approved plan.

1. Create the two application roots and their child directories with owner
   `gitlab-runner:gitlab-runner` and mode `0750`. Do not recursively change
   Docker-managed volume ownership.
2. Create the two server-only environment files from their reviewed templates,
   with different database credentials and JWT secrets. Set mode `0600`.
3. Install a dedicated protected project Shell runner named **Rainbow Test
   Shell Runner**, tagged `rainbow-test`, with untagged jobs disabled. Keep the
   existing Docker validation runner tagged `rainbow-ci` unchanged. Keep the
   separate protected **Rainbow Production Shell Runner** tagged
   `rainbow-production`; it must not carry the test tag.
4. Add the root-owned, mode-`0644` marker files required by preflight:
   `/etc/rainbow-fashions-test-runner` and
   `/etc/rainbow-fashions-production-runner`, each containing only
   `RAINBOW_DEPLOYMENT_RUNNER=1`.
5. Verify the `gitlab-runner` account can use Docker without `sudo`, and that
   it can write only the intended deployment root.

The CI preflight refuses a deployment when its path, Compose project, marker,
runner tag, required directories, environment-file permissions, or safe
environment constraints do not match.

## Nginx and TLS

Install the two separate virtual-host templates from `deployment/nginx/` only
after the old public frontend has been moved to production loopback port 8080.
Test proxies only to `127.0.0.1:8081`; production proxies only to
`127.0.0.1:8080`. Run `nginx -t` before each reload.

Confirm all three A records resolve to the Contabo server before requesting
certificates. Obtain separate certificates for the test hostname and the two
production hostnames, then run `certbot renew --dry-run`. Keep firewall access
limited to SSH, HTTP, and HTTPS; do not expose ports 5432, 8000, 8080, or 8081.

## CI/CD workflow

`shop-inventory` pipelines validate, package, and automatically deploy only
to test using the `rainbow-test` runner. They run local and public test health
checks at the test HTTPS domain. `main` pipelines run the same validation and
package stages, then offer a protected manual production deployment using only
the `rainbow-production` runner. Both deployment paths are serialized with
separate `resource_group` values.

Promotion is:

```text
feature/* → shop-inventory → automatic test deployment → acceptance
→ main → validation → manual production deployment
```

Do not create long-lived feature branches. Protect `shop-inventory` and
`main`; configure the `staging` and `production` GitLab environments as
protected. The deployment jobs must never be allowed to run on merge-request
validation pipelines.

## Backup, rollback, and emergencies

Before activation, the deployment job backs up the PostgreSQL database through
the explicit Compose project and verifies the backup is non-empty. An initial
test deployment is the sole exception because there is no existing test
database to back up. Production requires an active release and backup.

Activation creates a commit-specific release, updates only that environment's
`current` symlink, runs Alembic against the matching project, verifies one
head, and restores the previous application release symlink if activation
fails. A database migration cannot be automatically rolled back; use the
verified environment-specific backup and a reviewed recovery procedure.

Existing backup systemd units in `deployment/systemd/` now target production
explicitly. Do not install those units for test unchanged. If scheduled test
backups are required, create distinct `rainbow-test-*` units with
`RAINBOW_APP_ROOT=/opt/rainbow-fashions-test` and
`RAINBOW_COMPOSE_PROJECT=rainbow_test`.

## Existing deployment migration

1. Inventory the currently running containers, bindings, Compose project, and
   PostgreSQL volume.
2. Create and verify a PostgreSQL backup before changing the public frontend.
3. Confirm whether the existing database contains the real shop data. Preserve
   that volume for production; never seed test from it automatically.
4. Deploy production against the preserved production volume at loopback 8080
   and verify local health.
5. Enable the production Nginx host and verify production HTTPS.
6. Create the fresh isolated test stack at loopback 8081, then enable the test
   Nginx host and verify test HTTPS.
7. Leave the previous release available for rollback. Never use
   `docker compose down -v` on production and never run a database reset as
   part of this migration.
