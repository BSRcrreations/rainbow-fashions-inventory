# Installation Guide

## Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Create the PostgreSQL database and migrate it:

```bash
createdb inventory_db
alembic upgrade head
```

Run the API:

```bash
uvicorn app.main:app --reload
```

Create the initial owner through the approved development/test bootstrap workflow. Production deployments never seed users or catalog records automatically.

## Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open:

```text
http://localhost:5173
```
