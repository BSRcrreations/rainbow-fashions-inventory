# API Documentation

Base URL: `/api/v1`

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

- `GET /products?search=...&category_id=...&brand_id=...&is_active=true&low_stock=true`
- `POST /products`
- `GET /products/{product_id}`
- `PUT /products/{product_id}`
- `POST /products/{product_id}/image`
- `DELETE /products/{product_id}`

Validation:

- Duplicate barcode returns `409`.
- Duplicate category/brand/name/size/color variant returns `409`.
- Negative price, cost, quantity, or minimum stock returns `422`.
- MRP pricing requires an MRP value.

Purchases:

- `GET /purchases`
- `POST /purchases/upload`
- `GET /purchases/{purchase_id}`
- `PUT /purchases/{purchase_id}/review`
- `POST /purchases/{purchase_id}/confirm`

Stock:

- `GET /stock/history?product_id=...&movement_type=ADJUSTMENT`
- `GET /stock/history/export?product_id=...&movement_type=ADJUSTMENT`
- `POST /stock/adjustments`

Validation:

- Adjustment quantity must be positive.
- Decreases that would make stock negative return `400`.

Dashboard:

- `GET /dashboard/summary`

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
