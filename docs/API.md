# API Documentation

Base URL: `/api/v1`

Sales and hierarchy additions:

- `GET /categories/hierarchy` returns categories with their brands and subcategories.
- `GET|POST /subcategories` and `PUT|DELETE /subcategories/{id}` manage category-owned subcategories.
- `GET /brands?category_id={id}` filters brands by category; brand create requires `category_id`.
- Product create/update requires `category_id`, `subcategory_id`, and `brand_id`; mismatched parent categories return a validation error.
- Product `size` and `color` are optional compatibility fields. Create/update accepts optional `sizes: string[]` and `colors: string[]`; responses include linked `variants`. Supplying neither list creates a product without variants.
- `GET /sales/dashboard?preset=today|yesterday|week|month|custom` returns KPIs, trends, rankings, recent sales, and stock alerts. Custom ranges require `start_date` and `end_date`.
- `GET /sales` returns paginated, searchable sales history with payment and date filters.
- `POST /sales` creates an atomic sale and related stock movements.
- `GET /sales/{id}` returns invoice detail.
- `GET /sales/export?format=xlsx|pdf` exports the filtered history.
- `GET /stock/history` supports `product_id` and explicit `movement_type` filters and returns product/user attribution.
- `GET /stock/history/export` exports the filtered inventory movement audit trail.
- `POST /stock/adjustments` requires a reference and accepts `CUSTOMER_RETURN`, `SUPPLIER_RETURN`, `DAMAGE`, or `MANUAL_ADJUSTMENT` as its reason.
- `GET /sales` additionally supports `invoice_number`, `customer_name`, and `cashier_name` filters.

Authentication:

- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`

Roles:

- `OWNER`: full access
- `MANAGER`: operational access for purchases, inventory, reports, and billing
- `STAFF`: day-to-day access for product lookup, billing, purchases, and stock viewing

Categories:

- `GET /categories?search=...`
- `POST /categories`
- `GET /categories/{category_id}`
- `PUT /categories/{category_id}`
- `DELETE /categories/{category_id}`

Validation:

- Duplicate names return `409`.
- Empty or too-short names return `422`.
- Deleting a category referenced by products returns `400`.

Brands:

- `GET /brands?search=...`
- `POST /brands`
- `GET /brands/{brand_id}`
- `PUT /brands/{brand_id}`
- `DELETE /brands/{brand_id}`

Validation:

- Duplicate names return `409`.
- Empty or too-short names return `422`.
- Deleting a brand referenced by products returns `400`.

Products:

- `GET /products?search=...&category_id=...&brand_id=...&is_active=true`
- `GET /products?paginated=true&page=1&page_size=25&search=...&stock_status=low&min_price=100&max_price=1000&created_from=2026-01-01&created_to=2026-12-31&sort_by=name&sort_dir=asc`
- `GET /products/generate-code?kind=sku`
- `GET /products/generate-code?kind=barcode`
- `GET /products/export?format=csv`
- `GET /products/export?format=xlsx`
- `GET /products/import-template`
- `POST /products/import`
- `POST /products`
- `GET /products/{product_id}`
- `PUT /products/{product_id}`
- `POST /products/{product_id}/image`
- `DELETE /products/{product_id}/image`
- `DELETE /products/{product_id}`
- `POST /products/bulk/delete`
- `POST /products/bulk/category`
- `POST /products/bulk/brand`
- `POST /products/bulk/stock`
- `POST /products/bulk/export?format=csv`

Pagination response when `paginated=true`:

```json
{
  "items": [],
  "meta": {
    "page": 1,
    "page_size": 25,
    "total_records": 0,
    "total_pages": 1
  }
}
```

Supported product filters:

- `search`: SKU, barcode, product name, brand, category, size, or color.
- `category_id`
- `brand_id`
- `is_active`
- `stock_status`: `in`, `low`, or `out`.
- `min_price`
- `max_price`
- `created_from`
- `created_to`

Supported product sorting:

- `name`
- `sku`
- `selling_price`
- `purchase_price`
- `stock`
- `created_at`
- `updated_at`

Validation:

- Duplicate SKU returns `409`.
- Duplicate barcode returns `409`.
- Duplicate category/brand/name/size/color variant returns `409`.
- Negative price, cost, quantity, or minimum stock returns `422`.
- MRP pricing requires an MRP value.

Image rules:

- Product images accept `jpg`, `jpeg`, `png`, and `webp`.
- Maximum product image size is 5 MB.
- Images are stored with generated filenames.
- Products store a relative `image_url`, for example `/uploads/products/{filename}.webp`.
- `product_date` is required when creating a product and is returned with every product response.
- `GET /products/barcode/{barcode}` performs an authenticated exact barcode lookup and returns the normal product response with category, subcategory, brand, and variants. It is declared before the UUID product route.
- A missing barcode returns `404`; inactive and out-of-stock products are returned so POS can give the cashier a specific message.

Import/export:

- CSV import/export is supported.
- XLSX import/export is supported when `openpyxl` is installed.
- Invalid import rows are skipped and returned in an error report.
- Import expects existing brand and category names and a valid `product_date` in `YYYY-MM-DD` form.

Owner-only product deletion:

- `POST /products/bulk-delete-check` performs a store-scoped dependency preflight for selected products.
- `POST /products/bulk-delete` permanently deletes only products reported as eligible and requires `confirmation: "DELETE"`.
- `POST /products/bulk-purge-test-data` requires `confirmation: "PURGE TEST DATA"`, a reason, explicit `is_test_data`, and either a development/test environment or the store-level `allow_test_data_purge` flag.
- Every response includes a request ID. Ordinary permanent deletion rejects products with stock, inventory movements, purchase items, sale items, or another-store reference; it never cascades into business history.

Owner-confirmed transaction deletion:

- `POST /purchases/delete-check` and `POST /sales/delete-check` classify selected store-scoped records as permanent-delete eligible, void-and-reverse, or blocked.
- `POST /purchases/delete` and `POST /sales/delete` require an owner, a JSON `delete_password`, and an `Idempotency-Key` header. Passwords are verified only by the backend and are never returned, logged, or placed in audit snapshots.
- Draft/cancelled records without postings are permanently deleted. Posted purchases and completed sales are retained as `VOIDED` records with compensating stock movements in the same transaction.
- Configure deletion protection only with an Argon2id `DELETE_AUTH_PASSWORD_HASH` in the backend environment. Do not configure a plain-text `DELETE_AUTH_PASSWORD`; the configured hash is never returned by the API and cannot be changed through the browser.

Purchases:

- `GET /purchases`
- `GET /purchases/{purchase_id}` returns the complete store-scoped detail record, document metadata, processing job, totals, and audit history.
- `PATCH /purchases/{purchase_id}` updates only supplied draft/review fields and supports optimistic `version` checks.
- `POST /purchases/{purchase_id}/validate` validates invoice and item readiness without changing stock.
- `POST /purchases/{purchase_id}/cancel` cancels an unconfirmed purchase and records a reason.
- `GET /purchases/{purchase_id}/document` streams the protected original invoice without exposing a storage path.
- `POST /purchases/{purchase_id}/items`, `PATCH /purchases/{purchase_id}/items/{item_id}`, and `DELETE /purchases/{purchase_id}/items/{item_id}` manage editable draft lines.
- `POST /purchase-documents/upload` accepts multipart field `file` and returns `202 Accepted` with `document_id`, `job_id`, `request_id`, and `duplicate`. Re-uploading an identical document for the same store returns the existing document/job and does not schedule another job.
- `GET /purchase-documents/{document_id}` returns protected document metadata; `GET /purchase-documents/{document_id}/preview` streams the protected original for an authenticated member of that store.
- `GET /purchase-documents/jobs/{job_id}` reports queued, processing, review-ready, or failed recognition states.
- `POST /purchase-documents/{document_id}/retry` queues a failed document again and returns `202 Accepted`.
- `POST /purchases/from-document` creates the editable purchase draft after the job is `REVIEW_REQUIRED`.
- `GET /purchases/{purchase_id}`
- `PUT /purchases/{purchase_id}/review`
- `POST /purchases/{purchase_id}/confirm`

Purchase discount fields are additive and available on the existing purchase and
purchase-item create/update endpoints. Item lines accept a discount type,
percentage, per-unit or per-line amount, final unit price, free quantity, source,
and manual reason. Purchase headers accept an invoice discount type, value,
reason, and allocation method. The server calculates all persisted monetary
totals with decimal arithmetic; client totals are previews only. Free quantity is
included in received stock on confirmation but excluded from the invoice subtotal.
Discounts that exceed their eligible item or invoice amount return `422`.

Purchase upload validation:

- Supported invoices: JPG, JPEG, PNG, WEBP, HEIC, HEIF, and PDF.
- Maximum invoice size is 15 MB; extension, declared MIME type, and file signature must agree.
- Upload only stores the file and queues recognition. Stock changes only after `confirm`.
- Mock OCR never fabricates supplier, invoice, or item details; a real OCR provider must be configured for extraction.

Stock:

- `GET /stock/history?product_id=...&movement_type=MANUAL_ADJUSTMENT`
- `GET /stock/history/export?product_id=...&movement_type=MANUAL_ADJUSTMENT`
- `POST /stock/adjustments`

Validation:

- Adjustment quantity must be positive.
- Decreases that would make stock negative return `400`.

Dashboard:

- `GET /dashboard/summary`

Dashboard summary includes core inventory cards, low stock products, latest products, recent stock movements, stock distribution, category distribution, brand distribution, and a top-selling products placeholder.

FastAPI also serves interactive OpenAPI docs at `/docs` and raw OpenAPI JSON at `/api/v1/openapi.json`.

## Error Shape

API errors return a stable `detail` object:

```json
{
  "detail": {
    "message": "Validation failed",
    "code": "validation_error",
    "fields": [{ "field": "name", "message": "String should have at least 2 characters" }]
  }
}
```
# Sale corrections and returns

Sales are scoped to the authenticated user's store. Staff can create, view, list, export, and print invoices. Managers and owners can additionally edit, return, and void sales.

- `PATCH /api/v1/sales/{sale_id}` updates invoice items, payment, customer, and discount using the required optimistic-lock `version` and `edit_reason`.
- `POST /api/v1/sales/{sale_id}/returns` restores selected, still-returnable quantities and creates a customer-return record.
- `POST /api/v1/sales/{sale_id}/void` restores unreturned quantities and retains the invoice as `VOIDED`.
- `GET /api/v1/sales/{sale_id}/audit` and `GET /api/v1/sales/{sale_id}/returns` are manager/owner audit views.

All monetary values are recalculated server-side. A stale sale version returns `409 Conflict`.
# Purchase Intake

`POST /api/v1/purchase-documents/upload` stores a store-scoped invoice and returns `202 Accepted` before recognition begins. The client polls `GET /api/v1/purchase-documents/jobs/{job_id}`, can retry a failed job with `POST /api/v1/purchase-documents/{document_id}/retry`, and calls `POST /api/v1/purchases/from-document` only after the job is review-ready. It accepts JPG, JPEG, PNG, WEBP, HEIC/HEIF, and PDF invoices up to 15 MB, validates their signatures, and never updates stock. Duplicate documents return the existing job rather than creating another document or worker run. Every API error includes a request ID; document errors use safe codes such as `FILE_TOO_LARGE`, `CORRUPTED_FILE`, `ENCRYPTED_PDF`, and `HEIC_CONVERSION_NOT_AVAILABLE`.

`PUT /api/v1/purchases/{purchase_id}/review` requires `purchase_date`; it can include optional invoice and received dates plus `duplicate_acknowledged` when the duplicate warning has been reviewed. `POST /api/v1/purchases/{purchase_id}/confirm` is the only purchase action that writes inventory movements and stock.
