# Module Status

## Completed Foundation

- Authentication with JWT
- Role model: Owner, Manager, Staff
- Dashboard
- Categories
- Brands
- Products
- Purchases with invoice upload, OCR interface, review, and confirmation
- Inventory stock history
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
