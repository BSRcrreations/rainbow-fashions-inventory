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
