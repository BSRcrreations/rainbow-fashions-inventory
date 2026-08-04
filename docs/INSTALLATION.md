# Installation Guide

## Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set the required values in the local `.env` file. Do not commit it. Create the
PostgreSQL database and migrate it with the authoritative Alembic history:

```bash
createdb inventory_db
alembic upgrade head
```

Create the first owner exactly once. These values are placeholders; replace
them in your local shell and never commit real credentials:

```bash
OWNER_EMAIL=CHANGE_ME \
OWNER_PASSWORD=CHANGE_ME \
python scripts/bootstrap_owner.py \
  --store-name "CHANGE_ME" \
  --store-code "CHANGE_ME"
```

The command validates the password, creates a store when necessary, and stores
only a password hash. Re-running it is safe: an existing owner is left unchanged
unless `--update-existing` is supplied deliberately. If `OWNER_PASSWORD` is not
set, the command uses a hidden terminal prompt instead.

Run the API:

```bash
uvicorn app.main:app --reload
```

Production deployments never seed users or catalog records automatically.
## Frontend

```bash
cd frontend
npm ci
cp .env.example .env
npm run dev
```

Open `http://localhost:5173`.

The mobile application is an Expo scaffold, not a production-ready client.
