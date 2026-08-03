# Live Feature Verification Matrix

Audit date: 2026-08-03

Scope: `test/inventory-uat` only, using the isolated Docker stack at
`http://localhost:5174`, `http://localhost:8001`, and
`rainbow_inventory_test` on localhost port 5433. No production data or service
was used.

Status vocabulary is intentionally limited to: `DOCUMENTED`,
`BACKEND_READY`, `FRONTEND_CONNECTED`, `AUTOMATED_TESTED`, `UAT_VERIFIED`, and
`PRODUCTION_READY`. A status reflects the highest evidence collected during
this audit; no feature is marked `PRODUCTION_READY`.

| Area | Feature | Documentation source | Backend route/service | Database model | Frontend page/component | Automated evidence | Browser verification | Current status | Severity | Gap / recommended action | Evidence | Owner |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Auth | Login and owner session | README, API.md | `POST /auth/login`, `AuthService` | `users`, `stores` | `LoginPage`, `ProtectedRoute` | Backend suite | Owner login succeeded | UAT_VERIFIED | None | Add a disposable UAT account to browser smoke coverage | Owner identity rendered after login | Engineering |
| Auth | Staff/cashier permissions | MODULES.md, API.md | dependency guards | `users.role` | role-aware controls | Permission tests in backend suite | Not manually exercised | AUTOMATED_TESTED | Medium | Add browser role matrix | 148 backend tests passed | Engineering |
| Auth | Store isolation | ARCHITECTURE.md | scoped services/repositories | store foreign keys | no cross-store selector | Store-scope unit coverage | Not manually exercised | AUTOMATED_TESTED | High | Add two-store API/browser integration test | Existing isolated single-store seed | Engineering |
| Dashboard | Period metrics and empty states | MODULES.md | `GET /sales/dashboard`, `SaleService.dashboard` | sales, inventory, stock history | `SalesDashboardPage` | Health/dashboard coverage | Dashboard rendered zero-sales UAT state and inventory value | UAT_VERIFIED | None | Add seeded sales trend assertion | API request ID `e821cd3d-8a84-4cf1-a54c-fbb09a09de3a` | Engineering |
| Categories/Brands | Hierarchy, search, CRUD | MODULES.md, API.md | category/brand/subcategory routes/services | categories, brands, subcategories | `CategoriesPage` | Validation coverage partial | Not manually exercised | FRONTEND_CONNECTED | Medium | Complete CRUD browser journey | Hierarchy API returned 3 UAT categories | Engineering |
| Products | List, filters, pagination, search | API.md | `GET /products`, `ProductService.list_paginated` | products, variants | `ProductsPage` | Product tests | Product list showed 2 UAT products after load | UAT_VERIFIED | None | Add wait-for-loaded UI test | Paginated API request ID `4a5f06a4-e2de-4886-af31-e4d354a29a64` | Engineering |
| Products | Product metadata rename | MODULES.md | `PATCH /products/{id}` | products | `ProductsPage` edit dialog | `productEditLogic` tests | Rename persisted through page refresh; stock field remained disabled only | UAT_VERIFIED | None | Add full API integration assertion | `Full Leggings UAT Verified` persisted | Engineering |
| Products | Variant, size, colour visibility | BARCODE_FEATURE_README.md | product read service | product_variants | product table and sale selector | Barcode/variant unit tests | Six size variants visible, exact M selected | UAT_VERIFIED | None | Add colour-combination UAT fixture | Product and sale dialog both list size and colour | Engineering |
| Products | Images, import/export, deletion | API.md | product image/import/export/delete routes | products, deletion audits | `ProductsPage` dialogs | Partial service tests | Not manually exercised | FRONTEND_CONNECTED | Medium | Add browser upload/download/delete coverage | UI actions and routes exist | Engineering |
| Stock overview | Inventory and movement history | STOCK_RESET_AND_VARIANT_WORKFLOWS.md | `GET /stock/history` | stock_history, cost lots | `StockPage` | Stock tests | API returned 12 opening movements before UAT changes | BACKEND_READY | Medium | Add browser filter/export validation | Authenticated read-only API check | Engineering |
| Stock adjustment | Exact variant correction | STOCK_RESET_AND_VARIANT_WORKFLOWS.md | adjustment and correction routes | stock_history, stock_audit_events | `StockAdjustmentPage` | `test_stock_corrections.py` | Not manually exercised | AUTOMATED_TESTED | High | Add owner/staff UAT journey | Transaction-control guidance visible in product edit | Engineering |
| Stock reset | Preview, owner reset, audit | STOCK_RESET_AND_VARIANT_WORKFLOWS.md | reset preview/reset routes | stock audit events | `StockPage` reset panel | `test_stock_reset_service.py` | Not manually exercised | AUTOMATED_TESTED | High | Add separate reset fixture and browser test | No production reset performed | Engineering |
| Scan & Add Stock | Known barcode and exact variant staging | BARCODE_FEATURE_README.md, INVENTORY_UAT.md | stock scan routes/service | scan sessions, barcode mapping | `StockScanPage` | 14 onboarding and 4 scan page tests | Known barcode resolved to Prisma M | UAT_VERIFIED | None | Add unknown-barcode onboarding UAT | Browser displayed one exact M row | Engineering |
| Scan & Add Stock | Repeated manufacturer barcode | BARCODE_FEATURE_README.md | `POST /stock-scan/sessions/{id}/scan` | scan session items | `StockScanPage` | Barcode tests | Two scans remained one row with quantity 2 | UAT_VERIFIED | None | Add an API-level idempotency/repeat test against PostgreSQL | UI shows 1 unique variant / 2 scans | Engineering |
| Scan & Add Stock | Confirmed inventory posting | INVENTORY_UAT.md | `POST /stock-scan/sessions/{id}/confirm` | stock history, cost lots | confirmation dialog | Stock scan tests | Confirmed M changed from 19 to 21 and locked session | UAT_VERIFIED | None | Capture explicit stock-history request ID in test | Immutable confirmed session UI | Engineering |
| Purchases | Invoice intake, review, confirm | OCR_INTERFACE.md, MODULES.md | purchase/document routes/services | purchases, purchase_items, documents | Purchase pages | Purchase calculation tests | Not manually exercised | AUTOMATED_TESTED | High | Add invoice upload/poll/review UAT | No purchase seed was used | Engineering |
| Suppliers | Supplier CRUD, balances, payments, ledger | This audit | `/suppliers`, `SupplierService` | suppliers, supplier_payments, purchases | `SuppliersPage` | Backend suite, frontend build/typecheck/lint | Seeded suppliers rendered; proxy/API returned ARK distributors and GGl | UAT_VERIFIED | None | Add edit/delete browser journey and supplier purchase fixture | Authenticated API and browser UAT on 5174/8001 | Engineering |
| Customers | Customer CRUD, credit balances, payments, ledger | This audit | `/customers`, `CustomerService` | customers, customer_payments, sales.customer_id | `CustomersPage` | Backend suite, frontend build/typecheck/lint | Seeded customers rendered on desktop UAT page | UAT_VERIFIED | None | Add credit-sale browser journey and customer edit/delete coverage | Asha and Meena visible in browser UAT | Engineering |
| Expenses | Expense categories and expense entry | This audit | `/expenses`, `ExpenseService` | expense_categories, expenses | `ExpensesPage` | Backend suite, frontend build/typecheck/lint | Seeded rent expense rendered | UAT_VERIFIED | None | Add edit/delete and receipt upload coverage | `UAT monthly rent` visible in browser UAT | Engineering |
| Reports | Business summary, cash flow, inventory valuation | This audit | `/reports/summary`, `ReportService` | sales, purchases, expenses, payments, variants | `ReportsPage` | Backend suite, frontend build/typecheck/lint | P&L and inventory valuation rendered | UAT_VERIFIED | None | Add date-range assertions and export formats | Reports page browser UAT passed | Engineering |
| Sales | Product search, cart and exact variants | ARCHITECTURE.md, MODULES.md | sales catalog routes/services | sales, items, variants | `NewSalePage` | 14 New Sale tests | Cart line visibly rendered with M/Assorted/barcode and stock after sale | UAT_VERIFIED | None | Keep fixed cart-list regression test | 1 line/1 unit rendered | Engineering |
| Sales | Percentage discount and completion | API.md | `POST /sales`, `SaleService` | sales, sale_items, stock history | `NewSalePage` | sale discount tests | 10% changed INR 499.00 to INR 449.10; completed invoice | UAT_VERIFIED | None | Add fixed-discount UAT | Invoice `RF-20260803-318796` in isolated DB | Engineering |
| Sales history | List and persisted invoice | API.md | `GET /sales` | sales, sale_items | `SalesHistoryPage` | Service coverage partial | Completed UAT invoice appeared after navigation | UAT_VERIFIED | None | Add invoice details/export/void coverage | 1 completed invoice displayed | Engineering |
| Sales corrections | Edit, return, void | ARCHITECTURE.md, API.md | sale patch/return/void routes | sales audit/returns/history | `EditSalePage`, history actions | Backend coverage partial | Not manually exercised | AUTOMATED_TESTED | High | UAT zero-item/void/role checks | No destructive sale action beyond UAT completion | Engineering |
| Data protection | Backup status and restoration procedures | DATA_PROTECTION_BACKUP_RESTORE.md | `GET /security/backup-status` | backup process outside DB | Security settings | Backup status tests | Not manually exercised | BACKEND_READY | Blocker | Verify actual scheduler, restore drill, retention, and UI visibility | Documentation describes host operations only | DevOps |
| Deployment | CI, migration, health, rollback | CI_CD.md, DEPLOYMENT.md | Docker/GitLab scripts | Alembic | deployment configuration | Build, lint, typecheck executed locally | No deployment target used | DOCUMENTED | Blocker | Resolve migration/runtime divergence before any release | Current models exceed tracked Alembic head | DevOps |

## Audit-only findings

1. The UAT fixture originally used `.test` email addresses. The backend email
   validator correctly rejects those reserved domains, making browser login
   impossible. The deterministic fixture now uses valid `example.com`
   addresses.
2. `SupplierPayment` was missing its `supplier` relationship, preventing
   SQLAlchemy mapper configuration and all database-backed service work. A
   focused mapper test now protects the relationship.
3. Business-account migration `20260803_0037_business_accounts_expenses_reports.py`
   now covers suppliers, supplier payments, customers, customer payments,
   expense categories, expenses, and `sales.customer_id`. It was applied
   successfully to the isolated UAT database. It must be reviewed and committed
   with the associated models/routes/UI before any staging or production release.
