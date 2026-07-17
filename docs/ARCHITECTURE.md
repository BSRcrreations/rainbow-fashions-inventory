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
- Tables keep existing layout but use horizontal overflow and compact controls for tablet and phone widths.
