-- PostgreSQL table inventory for the Rainbow Fashions local database.
--
-- Run with:
--   psql "$DATABASE_URL" -f database/queries/inspect_tables.sql
--
-- The queries only read PostgreSQL metadata. They do not expose table data,
-- passwords, or other secrets.

-- 1. Application tables and estimated row counts (fast, based on statistics).
SELECT
    table_schema,
    table_name,
    table_type,
    COALESCE(
        (SELECT c.reltuples::bigint
         FROM pg_class AS c
         JOIN pg_namespace AS n ON n.oid = c.relnamespace
         WHERE n.nspname = t.table_schema
           AND c.relname = t.table_name),
        0
    ) AS estimated_rows
FROM information_schema.tables AS t
WHERE t.table_schema = 'public'
ORDER BY t.table_name;

-- 2. Columns, types, defaults, and nullability for every application table.
SELECT
    table_name,
    ordinal_position,
    column_name,
    data_type,
    udt_name AS postgres_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
ORDER BY table_name, ordinal_position;

-- 3. Primary keys, unique constraints, foreign keys, and check constraints.
-- pg_get_constraintdef preserves the exact definitions, including composite
-- keys, without duplicating column names in the result.
SELECT
    n.nspname AS table_schema,
    r.relname AS table_name,
    c.conname AS constraint_name,
    CASE c.contype
        WHEN 'p' THEN 'PRIMARY KEY'
        WHEN 'u' THEN 'UNIQUE'
        WHEN 'f' THEN 'FOREIGN KEY'
        WHEN 'c' THEN 'CHECK'
        WHEN 'x' THEN 'EXCLUSION'
    END AS constraint_type,
    pg_get_constraintdef(c.oid, true) AS definition
FROM pg_constraint AS c
JOIN pg_class AS r ON r.oid = c.conrelid
JOIN pg_namespace AS n ON n.oid = r.relnamespace
WHERE n.nspname = 'public'
ORDER BY r.relname, constraint_type, c.conname;

-- 4. Index definitions, including indexes created outside table definitions.
SELECT
    schemaname AS table_schema,
    tablename AS table_name,
    indexname AS index_name,
    indexdef AS definition
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
