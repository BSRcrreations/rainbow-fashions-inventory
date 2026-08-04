# Deployment

Deploy the FastAPI backend, React frontend, and PostgreSQL database with
protected host-managed environment files. Do not commit credentials, database
URLs, private keys, or generated backups.

1. Create a protected environment file from a reviewed template and set owner
   read/write permissions.
2. Start PostgreSQL and apply Alembic migrations.
3. Provision the first owner only with the approved bootstrap command; this
   base requires the pending security-bootstrap merge before that step.
4. Start backend and frontend, then verify liveness/readiness endpoints.
5. Verify backup creation and a non-production restore test before release.

Backup and restore scripts live under `deployment/scripts/`; their operational
status requires live verification and must not be inferred from source alone.
