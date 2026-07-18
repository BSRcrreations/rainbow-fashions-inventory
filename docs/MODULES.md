# Module Status

## Stage 1 Inventory Foundation

- Authentication with JWT login, logout acknowledgement, token validation, role validation, protected routes, token expiry handling, and structured errors.
- Dashboard summary cards, inventory value, low stock, and recent stock movements with loading, empty, and error states.
- Categories with create, edit, delete, search, duplicate validation, delete guard for referenced products, confirmation dialog, toasts, skeleton, empty state, and responsive layout.
- Brands with the same completed CRUD UX and backend rules as categories.
- Products with create/edit dialogs, advanced search, collapsible filters, filter chips, sorting, server-side pagination, active/inactive status, SKU, barcode, duplicate validation, compressed image upload/replace/delete, bulk operations, import/export, keyboard shortcuts, mobile cards, and desktop table views.
- Purchases with invoice upload, OCR review, editable review lines, confirmation flow, and stock changes only after confirmation.
- Stock with manual adjustments, stock history, filters, CSV export, validation, and negative-stock prevention.
- Dashboard improvements with latest products, distribution charts, and top-selling placeholder.
- Shared quality primitives: loading skeletons, empty states, toast notifications, accessible dialogs, error boundary, structured API errors, automatic expired-session logout, React Query caching, debounced search, and stricter client-side validation.

## Explicitly Not Included In Stage 1

- Billing
- Customers
- Supplier CRUD beyond purchase supplier capture
- Reports
- Android feature work
- Deployment changes

## Existing Scaffold Kept

- PWA installable web app
- Docker and Nginx deployment scaffolding
- PostgreSQL backup and restore scripts
- Android Expo scaffold

## Next Build Order

1. Customers
2. Suppliers full CRUD
3. Billing/POS
4. Expenses
5. Reports
6. Barcode scanner
7. Thermal printer
8. Settings
9. Backup and restore UI

## Engineering Rule

Before each module:

- Run backend syntax checks.
- Run frontend build.
- Fix existing errors.
- Reuse repositories, services, schemas, and UI primitives.

After each module:

- Run checks again.
- Update API and module docs.
- Produce a commit message.
