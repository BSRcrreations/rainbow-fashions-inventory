# Backend Audit

Stage 1 backend changes preserved the existing API -> services -> repositories -> models architecture.

Completed:

- Added structured API error responses and validation error formatting.
- Normalized authentication email input and added logout acknowledgement.
- Normalized category and brand names, blocked duplicates, and prevented deleting records referenced by products.
- Added category and brand search.
- Added product filters, case-insensitive duplicate variant and barcode checks, stricter text normalization, and product image upload support.
- Added product `image_url` schema/model/database support with Alembic migration.
- Confirmed purchase stock mutation remains isolated to purchase confirmation.
- Added purchase review text normalization and line-total recalculation.
- Added stock history filters and CSV export.
- Preserved negative-stock prevention.

Verification:

- `.venv/bin/python -m unittest discover tests`
- `.venv/bin/python -m compileall app tests`

Remaining backend issues:

- The project has no integration test database fixture yet, so current tests focus on validation and service guards.
- Existing PostgreSQL databases need the new Alembic migration applied for `products.image_url`.
