# Architecture

The backend follows a layered structure:

`API route -> Pydantic schema -> Service -> Repository -> SQLAlchemy model -> PostgreSQL`

Key decisions:

- JWT authentication is centralized in `core/security.py`.
- Role enforcement is centralized in `api/deps.py`.
- Database sessions are request-scoped through `database/session.py`.
- SQLAlchemy models mirror the PostgreSQL schema.
- Repository classes isolate persistence queries.
- Service classes own business rules and transaction boundaries.
- OCR is behind an interface in `app/ai`.
- Purchases are draft/review/confirm to prevent accidental stock changes.
- Catalog and product duplicate/delete rules live in services and repositories, not React.
- API errors are normalized in FastAPI exception handlers before reaching the client.
- Product images are stored as uploaded files and referenced from products by `image_url`.
- Product list enhancements are implemented in the product repository query layer and exposed through an additive `paginated=true` API mode, keeping the original list response backward compatible.
- Bulk product operations run through `ProductService` so duplicate checks and stock protections remain centralized.
- Import/export is handled by product API routes and service validation; invalid import rows are skipped and reported.
- `stores` and `product_inventory` support future multi-store work without redesign.

Future modules can add tables that reference existing IDs:

- Billing and POS can reference `products`, `stores`, and `stock_history`.
- Barcode and QR code modules can extend product identifiers without changing product variants.
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
