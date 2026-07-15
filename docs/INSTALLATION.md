# Installation Guide

## Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Create the PostgreSQL database:

```bash
createdb inventory_db
psql inventory_db -f ../database/schema.sql
psql inventory_db -f ../database/seed.sql
```

Run the API:

```bash
uvicorn app.main:app --reload
```

Default login:

```text
Rainbow@fashions.com / Fashions123
```

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
