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
# Purchase intake follow-up (2026-07-28)

- Replaced the silent all-mock OCR factory fallback with a configured local provider for text PDFs and supported images. The mock remains an explicit test-only setting.
- Added document hash serialization with a PostgreSQL advisory lock so concurrent identical uploads in one store resolve to the existing job without a destructive historical-document deduplication migration.
- Added protected purchase-document metadata and preview endpoints, guarded retries, structured safe file/OCR codes, and request IDs on API errors.
- The supplied `tests/fixtures/sample-invoice.pdf` is corrupt (reported as a zero-page PDF), so it cannot validate real Divya Sri extraction until the original invoice artifact is supplied.
