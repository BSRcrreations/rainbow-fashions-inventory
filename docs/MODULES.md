# Module Status

## Sales and Product Hierarchy

- Sales Dashboard: today/week/month/all-time KPIs, selected-range sales and profit trends, product/category/brand rankings, recent sales, low-stock, and out-of-stock signals.
- Sales History: debounced invoice/customer/payment/cashier search, date and payment filters, responsive invoice detail, print, PDF, and Excel export.
- Category hierarchy: brands and subcategories are managed inside Categories and cannot exist without a parent category.
- Product form: category-first selection loads only valid subcategories and brands. Color and size controls are opt-in, support multiple values, and persist as linked product variants.
- New Sale POS: stock-aware product search, cart quantities, customer/payment/discount capture, atomic checkout, invoice creation, profit calculation, stock decrement, and sale movement history.
- Inventory: current stock levels and a filterable audit trail with explicit purchase, sale, return, damage, and manual adjustment reasons.
- Stock Adjustment: separate manager workflow with a required reason, reference, and before/after stock preview.

## Stage 1 Inventory Foundation

- Authentication with JWT login, logout acknowledgement, token validation, role validation, protected routes, token expiry handling, and structured errors.
- Dashboard summary cards, inventory value, low stock, and recent stock movements with loading, empty, and error states.
- Categories with create, edit, delete, search, duplicate validation, delete guard for referenced products, confirmation dialog, toasts, skeleton, empty state, and responsive layout.
- Brands with the same completed CRUD UX and backend rules as categories.
- Products with create/edit dialogs, required product dates, automatic unique Code 128-compatible barcodes, barcode label printing, advanced search, collapsible filters, filter chips, sorting, server-side pagination, active/inactive status, SKU, duplicate validation, compressed image upload/replace/delete, bulk operations, import/export, keyboard shortcuts, mobile cards, and desktop table views.
- New Sale POS with a dedicated scanner-friendly barcode field. An Enter-terminated scan performs exact lookup, shows the matched product, and adds one unit without exceeding available stock.
- Purchases with invoice upload, OCR review, editable review lines, confirmation flow, and stock changes only after confirmation.
- Stock with manual adjustments, stock history, filters, CSV export, validation, and negative-stock prevention.
- Scan & Add Stock with persistent barcode sessions, exact-variant resolution, repeated-scan incrementing, quantity-entry mode, review, and one-time confirmation. Unknown barcodes open a verified onboarding dialog that supports assigning an existing variant, adding a variant under an existing product, or creating a new product; it includes category/brand selection, inline category/brand creation, package conversion, separate cost/MRP/selling prices, and optional editable OCR label suggestions.
- Barcode mappings are store scoped and audited separately from product variants. A barcode can represent an individual piece or a multipack; scan count and converted physical-piece count remain visible through review and confirmation.
- Physical counts append `STOCK_COUNT_IN` / `STOCK_COUNT_OUT` movements; opening stock appends `OPENING_STOCK` movements and creates cost lots.
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
6. Settings
7. Backup and restore UI

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
# Sales corrections, returns, and voids

The sales module keeps completed invoices immutable as financial records. Corrections append inventory movements and audit records instead of rewriting stock history. Sale edits use the difference between old and new quantities, customer returns restore only remaining quantities, and voiding restores every unreturned item.
# Purchase Intake

Purchases use a queue, draft, review, confirm workflow. The list opens a dedicated Purchase Details page with invoice preview, editable header fields, dates, payment details, item rows, live totals, inventory impact, processing diagnostics, and audit history. Upload commits the document and processing job before its background task begins; the client polls the store-scoped job, displays progress, and can retry a failed recognition. Re-uploading the same store-scoped document returns the existing job without duplicate processing. OCR output remains editable until confirmation and never invents supplier or invoice values. Purchase lines support explicit percentage, fixed, final-price, free-quantity, and manual discounts; invoice discounts can be allocated to cost or retained only as an invoice reduction. A confirmed line creates one exact sellable variant and one cost lot, preserving separate MRP/selling-price variants and historical costs. Purchase, invoice, received, due, created, updated, and confirmed dates remain distinct. Purchase records, documents, processing jobs, and document streaming are constrained to the authenticated user's store.

# Product Deletion

Products can be deactivated in bulk. Permanent deletion is owner-only and uses a preflight to distinguish unused products from products with stock or business history. A typed confirmation is required, deletion runs in one transaction, and `product_deletion_audits` retains the product identity and deleted-record counts after the product row is gone. Test-data purge is a separate owner-only action for explicitly flagged test products; it remains disabled by default and refuses to purge purchase or sale history.

# Owner-Confirmed Transaction Deletion

Purchase and sale deletion is owner-only and requires a server-verified deletion password. Draft or cancelled records with no postings can be permanently deleted; completed purchases and sales are voided and reversed instead, keeping their original business records. Preflight endpoints explain blocked records before the password dialog is shown. The backend records idempotency results, failed attempts, and durable destructive-action audits without storing passwords. Five failed attempts lock the action for fifteen minutes.
