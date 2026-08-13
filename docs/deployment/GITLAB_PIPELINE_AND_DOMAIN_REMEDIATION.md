# GitLab pipeline and domain deployment remediation

## Status

**NOT READY — no deployment has been run.** The GitLab job log for pipeline
`#205` could not be inspected because the GitLab CLI has no authenticated
session for the self-hosted GitLab host. The prior reported failure is treated
as an availability-preflight failure; runner name, executor, and tags remain
unverified until a project owner or maintainer authenticates.

## Corrected runner architecture

| Runner | Tag | Executor | Allowed work |
| --- | --- | --- | --- |
| CI runner | `rainbow-ci` | Docker | Tests, lint, typecheck, build, security checks, Gitleaks, and Compose build. |
| Production runner | `rainbow-production` | Shell on `178.238.237.182` | Release extraction, backup, migrations, service activation, and public verification. |

Every CI job is tagged. Production jobs inherit `rainbow-production`, a shared
`rainbow-fashions-production` resource lock, and rules requiring the protected
`shop-inventory` branch. The manual database-import job retains its explicit
manual-only protected-branch rules. Production jobs do not use Docker CI images
or install packages during execution.

If either runner is absent, deployment is blocked. Register locked, tagged
runners with untagged jobs disabled. Run these commands only on the respective
runner hosts with a project registration token obtained from GitLab:

```bash
# CI runner
gitlab-runner register --url https://vmi3446054.contaboserver.net \
  --executor docker --docker-image docker:27-cli \
  --tag-list rainbow-ci --locked=true --run-untagged=false

# Production host (178.238.237.182)
gitlab-runner register --url https://vmi3446054.contaboserver.net \
  --executor shell --tag-list rainbow-production \
  --locked=true --run-untagged=false
```

Do not give the CI Docker runner access to the production Docker socket, the
production filesystem, or the production environment file.

### GitLab runner UI configuration (project Owner/Maintainer action)

Runner tags and protection are stored by GitLab and cannot be established by
editing `.gitlab-ci.yml` or the runner's local `config.toml`. In **Settings →
CI/CD → Runners**, confirm the following configuration before allowing a
deployment pipeline to run:

| Runner | Executor | Tags | Run untagged | Protected | Locked to project |
| --- | --- | --- | --- | --- | --- |
| Rainbow CI Docker Runner | Docker | `rainbow-ci` only | Off | Off (unless required by project policy) | On |
| Rainbow Production Shell Runner | Shell on `178.238.237.182` | `rainbow-production` only | Off | On | On |

Remove `rainbow-production` and the obsolete
`rainbow-fashions-prod-runner` tag from the Docker runner. Never assign both
tags to one runner. The production runner must be registered on Contabo, not
on a developer workstation, and must be online before a deployment pipeline is
started. `shop-inventory` must remain a protected branch.

The decisive job-log evidence is:

```text
Preparing the "shell" executor
```

If a job tagged `rainbow-production` reports a Docker executor, cancel it and
correct GitLab's runner configuration; do not add host packages to a CI image.

## Domain preflight and DNS

`verify_domain_preflight` now uses `DNS_ONLY=true`. It validates registration,
delegation, A/AAAA records, resolver agreement, and the expected IPv4 address,
but deliberately does not make an HTTP or HTTPS request before deployment.
HTTP, HTTPS, redirect, health, and smoke checks run only in
`deploy_phase_4_verify` after the stack is activated.

The read-only DNS-only preflight completed successfully on 2026-08-04: the
test A record and the system, Cloudflare, and Google resolver answers agree on
the expected IPv4 address; no AAAA record was returned. HTTP and HTTPS were not
probed by this preflight.

Required records:

| Name | Type | Value |
| --- | --- | --- |
| `test` | A | `178.238.237.182` |
| `@` | A | `178.238.237.182` |
| `www` | A or CNAME | `178.238.237.182` or `rainbow-fashions.in` |

Do not add an IPv6 record unless the host is configured for it. Wait for the
authoritative resolver and public resolver answers to agree before deployment.

## Production shell-runner bootstrap

Install and maintain these tools through the server bootstrap process, not CI:

- Docker Engine and Docker Compose plugin
- GitLab Runner (shell executor)
- Nginx, Certbot, curl, OpenSSL, Bash, and Git

Create and grant the deployment user access to:

```text
/opt/rainbow-fashions/releases
/opt/rainbow-fashions/shared
/opt/rainbow-fashions/backups
/opt/rainbow-fashions/runtime/uploads
/opt/rainbow-fashions/runtime/opening-stock-imports
/opt/rainbow-fashions/runtime/backups/status
```

The shell-runner preflight requires the host-level environment file at
`/opt/rainbow-fashions/shared/backend.env` to be mode `600`, owned by the
deployment user, free of placeholders, configured for production, and to
contain the required CORS origins. It checks properties only and never prints
file contents. The preflight also requires at least 5 GiB free space.

It additionally requires this root-owned, non-secret host marker:

```text
/etc/rainbow-fashions-production-runner
RAINBOW_PRODUCTION_RUNNER=1
```

Create it with mode `644`. Its absence deliberately fails the preflight with
`this job is not running on the approved production shell runner`, preventing a
Docker CI container from being mistaken for the deployment host.

## Safe deployment sequence

1. Package the release on `rainbow-ci`.
2. Extract it into a commit-specific release directory on `rainbow-production`.
3. Run the host preflight.
4. Create and verify a non-empty PostgreSQL backup.
5. Switch the `current` symlink, build containers, start PostgreSQL, and run
   `alembic upgrade head`.
6. Stop if application tables exist without `alembic_version`; use a separate,
   reviewed schema-baseline procedure instead.
7. Start the complete stack, check local health, public HTTPS health, redirect,
   and smoke tests. Preserve the previous release for rollback.

The pipeline never runs `alembic stamp head` against an unknown production
database.

## Nginx and HTTPS

The host configuration covers `test.rainbow-fashions.in`,
`rainbow-fashions.in`, and `www.rainbow-fashions.in`, proxies to
`127.0.0.1:8080`, retains the required forwarding headers, permits 15 MiB
uploads, and redirects HTTP only after certificates are installed.

After DNS resolves correctly and Nginx is enabled, obtain certificates on the
production host:

```bash
certbot --nginx \
  -d test.rainbow-fashions.in \
  -d rainbow-fashions.in \
  -d www.rainbow-fashions.in
```

Do not run Certbot before DNS delegation and all required records resolve.

## Validation and remaining blockers

The pipeline now contains Python compile, full backend test, Alembic-head and
OpenAPI checks; frontend install/test/lint/typecheck/build plus an explicit
protected exception policy for high/critical production dependency advisories;
secret, fixed-password-hash, artifact, Gitleaks, and Compose checks.

### Local validation results

| Check | Result |
| --- | --- |
| Backend and deployment tests | Passed: 196 tests (one existing Argon2 deprecation warning). |
| Frontend tests | Passed: 52 tests. |
| Frontend lint, typecheck, and build | Passed (non-failing bundle-size warning). |
| Secret, fixed-password-hash, and artifact checks | Passed. |
| Gitleaks pinned scanner | Passed with redacted output. |
| Production dependency audit | Passed at the high/critical threshold. |
| Docker Compose configuration | Passed using the CI-safe placeholder environment file. |
| Docker Compose build | Blocked: the local Docker daemon is unavailable. |
| CI YAML parse | Passed locally; GitLab CI lint is blocked by unavailable GitLab authentication. |
| DNS-only test suite and live DNS-only preflight | Passed. |
| Nginx configuration test | Passed statically; host `nginx -t` remains required after installation. |

Before merge or deployment, a project owner must:

1. Authenticate to GitLab and inspect pipeline `#205` and its failed job.
2. Register and verify both runner classes.
3. Configure the protected `shop-inventory` branch and the production runner.
4. Configure the DNS records, then Nginx and TLS.
5. Run the pipeline checks and a disposable deployment test.
6. Confirm both remotes have no unique `shop-inventory` commits, then
   fast-forward the branch to `main` without force-pushing and confirm the
   GitHub and GitLab trees match.

No production data, credentials, history, or branch protections were changed
while preparing this remediation.
