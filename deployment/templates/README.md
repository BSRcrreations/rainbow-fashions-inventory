# Production backend environment

Use [backend.production.template](backend.production.template) only as a
safe template. The real server environment file must be located at:

```text
/opt/rainbow-fashions/shared/backend.env
```

The real file must never be committed, copied into a release artifact, or
stored as a GitLab artifact. It is ignored by Git when a local copy is made in
this directory.

## Server setup

Create the server file from this template, replace every `CHANGE_ME` value, and
then restrict its permissions:

```bash
sudo mkdir -p /opt/rainbow-fashions/shared
sudo cp deployment/templates/backend.production.template /opt/rainbow-fashions/shared/backend.env
sudo chmod 600 /opt/rainbow-fashions/shared/backend.env
```

Generate the database password with:

```bash
openssl rand -hex 32
```

Generate the JWT secret with:

```bash
openssl rand -hex 64
```

Set `POSTGRES_PASSWORD` and the password embedded in `DATABASE_URL` to the
same generated database password. The URL must follow this exact relationship:

```text
postgresql+psycopg://<POSTGRES_USER>:<POSTGRES_PASSWORD>@postgres:5432/<POSTGRES_DB>
```

Keep `APP_ENV=production` and `DEBUG=false`. Set `CORS_ORIGINS` to the final
HTTPS testing or production hostname, for example
`https://test.rainbow-fashions.in`.

The deployment pipeline rejects empty required values, placeholder values such
as `CHANGE_ME`, the old `inventory123` password, a JWT secret shorter than 64
characters, and a `DATABASE_URL` that does not match the Postgres values. This
is intentional: replace all placeholders before deploying.

## Apply production hardening

After reviewing the production environment file and ensuring a backup plan is
in place, copy the hardening script to the production server and run it as
root:

```bash
scp deployment/scripts/apply_production_hardening.sh root@178.238.237.182:/root/
ssh root@178.238.237.182
chmod +x /root/apply_production_hardening.sh
/root/apply_production_hardening.sh
```

The script validates the environment without printing secrets, creates a new
custom-format PostgreSQL backup under
`/opt/rainbow-fashions/backups/manual-hardening`, synchronizes the configured
database-role password, runs migrations, and waits for the local health check.
It does not configure HTTPS, drop or recreate the database, remove old
backups, or delete Docker volumes.
