# Purchase Workflow Audit - 2026-07-28

## Baseline

- **Frontend:** React 18.3.1, Vite 8.1.5, TypeScript 5.6.2, Tailwind CSS 3.4.13, React Query 5.101.2.
- **Backend:** FastAPI 0.115.0, SQLAlchemy 2.0.34, Pydantic 2.8.2, Alembic 1.13.2, PostgreSQL through psycopg 3.2.13.
- **Database/session:** `Settings.database_url` configures one SQLAlchemy `SessionLocal` per request through `get_db`; background document processing creates its own `SessionLocal`.
- **Alembic:** local database is at `20260728_0013` (current head).
- **API base URL:** the frontend defaults to `http(s)://<browser-host>:8000/api/v1`, overrideable through `VITE_API_BASE_URL`.
- **Authentication and store context:** JWT bearer tokens resolve the `User`; each purchase/document query derives `store_id` from `current_user.store_id`.
- **Background processing:** FastAPI `BackgroundTasks` invokes local in-process document work after a successful upload response.
- **Proxy:** the Docker frontend proxy already limits uploads to 15 MB; `deployment/nginx/rainbow-fashions.conf` is inconsistent at 20 MB and proxies to local development ports.

## Current Purchase Flow

1. `POST /purchase-documents/upload` saves the file, creates `PurchaseDocument` and `DocumentProcessingJob`, and returns 202.
2. A local background task updates the job through preprocessing, OCR, extraction, and review-required statuses.
3. The purchase list polls the job and calls `POST /purchases/from-document` once review is ready.
4. A purchase draft stores editable values and items; confirmation creates `StockHistory` rows and increments existing cached stock values in the same session.

## Root Causes and Risks

- `MockOCRService` always returns an empty string. `app.ai.factory` also returns that mock for every configured provider. A real invoice can therefore upload and reach review, but it cannot produce the supplied Divya Sri Textiles values without a configured, tested recognizer. This is the direct cause of missing extracted invoice data, not a frontend rendering issue.
- The historical synchronous `POST /purchases/upload` still runs OCR in the request. The frontend uses the asynchronous endpoint, but retaining two divergent ingestion paths risks future regressions.
- Purchase-document upload lacks a store/hash uniqueness constraint and retry does not prevent a second active job. Repeated uploads can create duplicate document records and background work.
- The API client exposes a generic message for all 5xx responses and discards request IDs and nested structured errors, making actionable backend failures look identical.
- The current `products` table is a legacy product record with optional `size` and `color`; `ProductVariant` contains only product, size, color, and timestamp. Neither table has the requested complete base-product/variant/store fields. A safe migration must be staged, not inferred from invoice text.
- `StockHistory` is append-only, but confirmation also mutates `products.current_stock` and `product_inventory.current_stock`. This is a cached balance design, not the requested ledger-as-source-of-truth design. Reconciliation must precede any switch in valuation or stock calculation.
- Categories, brands, and subcategories are now store scoped by `20260728_0013`, but products and suppliers remain global. That is a tenant-isolation gap for later schema work.
- Existing ARK references occur only in historical cleanup migrations (`20260727_0010` and `20260727_0011`); there is no frontend demo fallback to remove. Those cleanup statements must remain for upgrade safety.
- The supplied local fixture reports as a zero-page PDF and no text-PDF library is installed. It cannot currently prove the required invoice extraction acceptance result.

## Focused Implementation Plan

1. **Document intake and observability:** add store/hash duplicate protection, active-job retry protection, secure document metadata/preview endpoints, request-ID-aware failures, and specific file/recognition failure codes.
2. **Purchase draft integrity:** keep one asynchronous creation path, preserve editable header/item values, improve grouped product classification, and make validation errors field-addressable.
3. **Product and tenancy migration design:** add a separate, reversible base-product/variant/store migration only after a data backfill/reconciliation report is approved. Do not transform existing products or invent brands from suppliers.
4. **Ledger evolution:** retain `StockHistory` as the existing transaction journal, add reconciliation coverage, then introduce the richer inventory ledger and location/condition semantics incrementally.
5. **Remaining domains:** purchase orders, goods receipts, returns, exchanges, stock counts, landed costing, reorder reporting, and deployment worker infrastructure require new models and routes. They are not present today and cannot be represented as complete without dedicated migrations, UI, and integration tests.

## File-by-File Implementation Map

- `backend/app/services/purchase_document_service.py`: document hash serialization, duplicate retrieval, retry locking, job failure mapping, and background job lifecycle.
- `backend/app/services/file_service.py`: file-size, signature, and media-type validation codes.
- `backend/app/ai/base.py`, `backend/app/ai/factory.py`, `backend/app/ai/local_ocr.py`: provider abstraction and local text-PDF/image recognition.
- `backend/app/api/routes/purchase_documents.py` and `backend/app/schemas/purchase.py`: accepted-upload, metadata, preview, retry, and provider response contracts.
- `backend/app/main.py`, `backend/app/core/exceptions.py`, and `frontend/src/api/client.ts`: request-ID-aware structured errors with a safe network fallback.
- `frontend/src/components/ErrorState.tsx` and `frontend/src/pages/PurchaseDetailPage.tsx`: inline message, field, code, and request-ID presentation.
- `backend/tests/test_local_ocr.py` and `backend/tests/test_stage1_validation.py`: local OCR and route/provider regression coverage.
- `backend/requirements.txt`, `backend/.env.example`, `docs/OCR_INTERFACE.md`, and deployment/docs files: runtime dependency, safe provider configuration, and operations documentation.

## Baseline Quality Gates

- `PYTHONPYCACHEPREFIX=/tmp/rainbow-pyc ./.venv/bin/pytest -q` - **28 passed**.
- `npm run typecheck && npm run lint && npm run build` - **passed**.
- `alembic current` / `alembic heads` - **20260728_0013 (head)**.
