# API Documentation

Base URL: `/api/v1`

Authentication:

- `POST /auth/login`
- `GET /auth/me`

Roles:

- `OWNER`: full access
- `MANAGER`: operational access for purchases, inventory, reports, and billing
- `STAFF`: day-to-day access for product lookup, billing, purchases, and stock viewing

Categories:

- `GET /categories`
- `POST /categories`
- `GET /categories/{category_id}`
- `PUT /categories/{category_id}`
- `DELETE /categories/{category_id}`

Brands:

- `GET /brands`
- `POST /brands`
- `GET /brands/{brand_id}`
- `PUT /brands/{brand_id}`
- `DELETE /brands/{brand_id}`

Products:

- `GET /products?search=...`
- `POST /products`
- `GET /products/{product_id}`
- `PUT /products/{product_id}`
- `DELETE /products/{product_id}`

Purchases:

- `GET /purchases`
- `POST /purchases/upload`
- `GET /purchases/{purchase_id}`
- `PUT /purchases/{purchase_id}/review`
- `POST /purchases/{purchase_id}/confirm`

Stock:

- `GET /stock/history`
- `POST /stock/adjustments`

Dashboard:

- `GET /dashboard/summary`

FastAPI also serves interactive OpenAPI docs at `/docs` and raw OpenAPI JSON at `/api/v1/openapi.json`.
