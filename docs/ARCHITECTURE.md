# Architecture

The frontend presentation layer uses the centralized token and component contract documented in `docs/DESIGN_SYSTEM.md`. Pages consume semantic Tailwind aliases and shared UI primitives; they do not own independent color schemes or control styling.

## Sales and Catalog Integrity

The existing `route -> schema -> service -> repository -> model -> PostgreSQL` layering is retained. Category owns both SubCategory and Brand, while Product references all three. Composite database foreign keys plus service validation prevent assigning a brand or subcategory from another category.

The hierarchy migration creates a `General` subcategory for every existing category and clones a legacy brand when it was shared by products in multiple categories. Sales use immutable invoice headers and item snapshots. `SaleService.create` locks product rows, calculates revenue/cost/profit server-side, updates product and store inventory, and writes linked stock history in one transaction.

All inventory changes use explicit movement reasons. Confirmed purchases write `PURCHASE`, POS checkout writes `SALE`, and the separate adjustment service validates customer returns, supplier returns, damage, or manual corrections. Every movement stores the product, quantity, before/after stock, reference, user, and timestamp.

The backend follows a layered structure:

`API route -> Pydantic schema -> Service -> Repository -> SQLAlchemy model -> PostgreSQL`

Key decisions:

- JWT authentication is centralized in `core/security.py`.
- Role enforcement is centralized in `api/deps.py`.
- Database sessions are request-scoped through `database/session.py`.
- SQLAlchemy models mirror the PostgreSQL schema.
- Repository classes isolate persistence queries.
- Service classes own business rules and transaction boundaries.
- OCR is behind an interface in `app/ai`. The local provider reads text-native PDFs through `pypdf` and invokes Tesseract for supported images, returning explicit safe failures when a format requires unavailable conversion or image-PDF OCR.
- Purchases are queue/draft/review/confirm to prevent accidental stock changes; upload commits the job before background recognition begins. Purchase edits use optimistic versions and append purchase audit records; only confirmation writes stock history. `services/discount_calculator.py` is the server-side decimal authority for purchase discount, tax, invoice allocation, and free-quantity cost calculations.
- `ProductVariant` is the store-scoped sellable inventory identity. `InventoryCostLot` preserves each received variant cost and remaining quantity. POS sale creation locks variants and lots, writes immutable sale snapshots and variant-linked stock movements, and keeps `Product.current_stock` and `product_inventory` as compatibility aggregates for existing reports.
- `StockScanSession` is a store-scoped persistent draft. Barcode lookup resolves one `ProductVariant`; confirmation locks the session and variants, appends explicit count/opening movements, updates compatibility aggregates and cost lots, then commits once.
- `ProductBarcode` is the store-scoped barcode identity layer. It maps each scanner value to one exact sellable variant and package configuration, preserves string/leading-zero identifiers, stores package-to-base-piece conversion, and records each assignment in `ProductBarcodeAudit`. Scan-session lines are keyed by barcode mapping so different package configurations for the same variant never merge accidentally.
- Barcode onboarding remains a service-level transaction: the service locks the store-scoped scan session and barcode namespace, validates the exact category/brand hierarchy, creates the selected product/variant only when requested, creates its audited mapping, then adds the package-aware draft line. No stock is posted until the existing session confirmation transaction runs.
- Catalog and product duplicate/delete rules live in services and repositories, not React.
- API errors are normalized in FastAPI exception handlers before reaching the client. Error payloads and response headers include a request ID, while the frontend keeps error presentation separate from transport so a request can produce one local toast and one optional inline state.
- Product images are stored as uploaded files and referenced from products by `image_url`.
- Product list enhancements are implemented in the product repository query layer and exposed through an additive `paginated=true` API mode, keeping the original list response backward compatible.
- Bulk product operations run through `ProductService` so duplicate checks and stock protections remain centralized.
- Destructive product operations are isolated in `ProductDeletionService`: it locks selected rows, derives the store from the authenticated owner, checks dependent records, records immutable deletion audits, and commits or rolls back as a single unit.
- Purchase and sale deletion is handled by `DestructiveActionService`. It verifies only the environment-managed Argon2id `DELETE_AUTH_PASSWORD_HASH`, rate-limits failed attempts by store and user, requires idempotency keys, and creates immutable audit records without storing passwords.
- Import/export is handled by product API routes and service validation; invalid import rows are skipped and reported.
- `stores` and `product_inventory` support future multi-store work without redesign.

Future modules can add tables that reference existing IDs:

- Billing and POS can reference `products`, `stores`, and `stock_history`.
- Product barcodes use the existing `products.barcode` column. Product dates, exact barcode lookup, and Code 128 label rendering extend the catalog without a separate identifier table.
- Supplier and customer modules can expand from the existing supplier-ready purchase design.
- Mobile apps can use the same REST API.

## Client Targets

- Web: React, Vite, TypeScript, Tailwind CSS, shadcn-style primitives, TanStack Query, Zustand.
- Android: React Native Expo scaffold using the same API and authentication model.
- iOS: intentionally out of scope.

## Stage 1 Frontend Pattern

- Pages reuse shared primitives for buttons, cards, skeletons, empty states, confirmation dialogs, toasts, and error display.
- Form validation runs client-side for fast feedback, while backend services remain the source of truth.
- Dense desktop tables switch to task-focused mobile cards where horizontal scrolling would hide important actions.
- Products use React Query caching, debounced search, memoized pagination state, and server-side filtering/sorting.
- Product create/edit runs in a reusable accessible dialog; advanced filters remain collapsible and expose removable active-filter chips.
- API `401` responses clear the local token and notify the authentication provider so protected routes return to login immediately.
# Sale workflow integrity

Sale edits, returns, and voids run in one database transaction. The service locks the sale, products, and authenticated-store inventory rows, recalculates totals with `Decimal`, creates stock history rows, and writes a `sale_audits` record before committing once.
