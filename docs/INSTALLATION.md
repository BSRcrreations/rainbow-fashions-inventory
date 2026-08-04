# Installation Guide

## Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
createdb inventory_db
psql inventory_db -f ../database/schema.sql
uvicorn app.main:app --reload
```

Keep the real environment file outside Git and do not use published/default
credentials. This base does not yet include the approved owner-bootstrap
command; merge the security bootstrap change before provisioning an owner.

## Frontend

```bash
cd frontend
npm ci
cp .env.example .env
npm run dev
```

The mobile application is an Expo scaffold, not a production-ready client.
