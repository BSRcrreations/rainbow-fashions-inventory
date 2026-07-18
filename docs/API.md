# API Documentation

Base URL: `/api/v1`

Sales and hierarchy additions:

- `GET /categories/hierarchy` returns categories with their brands and subcategories.
- `GET|POST /subcategories` and `PUT|DELETE /subcategories/{id}` manage category-owned subcategories.
- `GET /brands?category_id={id}` filters brands by category; brand create requires `category_id`.
- Product create/update requires `category_id`, `subcategory_id`, and `brand_id`; mismatched parent categories return a validation error.
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

Import/export:

- CSV import/export is supported.
- XLSX import/export is supported when `openpyxl` is installed.
- Invalid import rows are skipped and returned in an error report.
- Import expects existing brand and category names.

Purchases:

- `GET /purchases`
- `POST /purchases/upload`
- `GET /purchases/{purchase_id}`
- `PUT /purchases/{purchase_id}/review`
- `POST /purchases/{purchase_id}/confirm`

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
