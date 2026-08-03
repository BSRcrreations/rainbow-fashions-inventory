# Live Feature Verification

Audit date: 2026-08-03

Scope: Rainbow Fashions Inventory, deployment branch `shop-inventory`.

Live targets:

- Current application: `http://178.238.237.182`
- Future hostname: `https://test.rainbow-fashions.in`

Verification rules used in this audit:

- Code, migrations, API docs, and tests are evidence that a feature exists, not proof that it works live.
- `WORKING` is reserved for features verified through the deployed UI with the correct role, API request, persistence, refreshed UI state, and automated coverage.
- No production inventory mutations were performed during this audit.

## Live Reachability Notes

- `GET http://178.238.237.182/` returned the deployed React shell with `200 OK`.
- `GET http://178.238.237.182/api/v1/openapi.json` returned OpenAPI JSON, so the public API route is reachable.
- `GET http://178.238.237.182/api/v1/auth/me` returned `401` with a structured request ID, so unauthenticated API protection is active.
- `GET http://178.238.237.182/health/live` returned frontend HTML instead of backend health JSON. Use `/api/v1/openapi.json` or fix Nginx health routing before relying on root-level health probes.
- Authenticated live workflow verification was not completed because submitting the owner password from this environment was rejected by the approval reviewer. Use a disposable test credential or run the smoke script from the deployment host.
- `test.rainbow-fashions.in` remains future-only until DNS delegation is repaired and HTTPS is provisioned.

## Truth Matrix

| Module | Documented | Backend Exists | Frontend Exists | API Connected | Tested | Live Verified | Status |
|--------|------------|----------------|-----------------|---------------|--------|---------------|--------|
| Login and roles | Yes | Yes | Yes | Yes | Partial backend | Partial reachability only | NOT_LIVE_VERIFIED |
| Dashboard | Yes | Yes | Yes | Yes | Backend health/dashboard coverage only | No authenticated UI check | NOT_LIVE_VERIFIED |
| New Sale | Yes | Yes | Yes | Yes | Component/unit tests | No authenticated UI sale check | NOT_LIVE_VERIFIED |
| Barcode scanning | Yes | Yes | Yes | Yes | Unit/service tests | No authenticated scanner check | NOT_LIVE_VERIFIED |
| Product search | Yes | Yes | Yes | Yes | Component/backend coverage partial | No authenticated UI check | NOT_LIVE_VERIFIED |
| Variant selection | Yes | Yes | Yes | Yes | Component/unit tests | No authenticated UI check | NOT_LIVE_VERIFIED |
| Current Sale/cart | Yes | Yes | Yes | Yes | Component/unit tests | No authenticated UI check | NOT_LIVE_VERIFIED |
| Discounts | Yes | Yes | Yes | Yes | Frontend/backend discount tests | No live checkout check | NOT_LIVE_VERIFIED |
| Payment methods | Yes | Yes | Yes | Yes | Covered through sale schemas/service partially | No live checkout check | NOT_LIVE_VERIFIED |
| Complete Sale | Yes | Yes | Yes | Yes | Backend sale tests partial | No live mutation performed | NOT_LIVE_VERIFIED |
| Sales History | Yes | Yes | Yes | Yes | Backend/API coverage partial | No authenticated UI check | NOT_LIVE_VERIFIED |
| Edit Sale | Yes | Yes | Yes | Yes | Backend/service coverage partial | No authenticated UI check | NOT_LIVE_VERIFIED |
| Void Sale | Yes | Yes | Yes | Yes | Backend/service coverage partial | No live mutation performed | NOT_LIVE_VERIFIED |
| Returns | Yes | Yes | Frontend detail/actions exist | Yes | Backend/service coverage partial | No live mutation performed | NOT_LIVE_VERIFIED |
| Purchases | Yes | Yes | Yes | Yes | Backend purchase tests | No authenticated UI check | NOT_LIVE_VERIFIED |
| Categories | Yes | Yes | Yes | Yes | Backend validation partial | No authenticated UI check | NOT_LIVE_VERIFIED |
| Subcategories | Yes | Yes | Yes | Yes | Backend validation partial | No authenticated UI check | NOT_LIVE_VERIFIED |
| Brands | Yes | Yes | Yes | Yes | Backend validation partial | No authenticated UI check | NOT_LIVE_VERIFIED |
| Products | Yes | Yes | Yes | Yes | Product metadata tests | No authenticated UI check | NOT_LIVE_VERIFIED |
| Product variants | Yes | Yes | Partial product form/stock scan flows | Yes | Barcode/onboarding tests | No authenticated UI check | NOT_LIVE_VERIFIED |
| Barcode assignments | Yes | Yes | Yes | Yes | Barcode onboarding/transfer tests | No authenticated UI check | NOT_LIVE_VERIFIED |
| Stock Overview | Yes | Yes | Yes | Yes | Backend stock tests partial | No authenticated UI check | NOT_LIVE_VERIFIED |
| Scan & Add Stock | Yes | Yes | Yes | Yes | Frontend/backend scan tests | No live stock mutation performed | NOT_LIVE_VERIFIED |
| Opening Stock | Yes | Yes | Yes through stock scan | Yes | Backend/service partial | No live stock mutation performed | NOT_LIVE_VERIFIED |
| Physical Count | Yes | Yes | Yes through stock scan | Yes | Backend/service partial | No live stock mutation performed | NOT_LIVE_VERIFIED |
| Stock Adjustment | Yes | Yes | Yes | Yes | Stock correction/reset tests | No live stock mutation performed | NOT_LIVE_VERIFIED |
| Stock corrections | Yes | Yes | Yes | Yes | Backend tests | No live mutation performed | NOT_LIVE_VERIFIED |
| Product editing | Yes | Yes | Yes | Yes | Product payload tests | No authenticated UI check | NOT_LIVE_VERIFIED |
| Product archive | Yes | Yes | Frontend action exists | Yes | Product deletion/archive service partial | No live mutation performed | NOT_LIVE_VERIFIED |
| Product deletion | Yes | Yes | Yes, owner-only guarded | Yes | Product deletion tests | No live mutation performed | NOT_LIVE_VERIFIED |
| Audit history | Yes | Yes | Partial sales/purchase/stock views | Yes | Backend audit/deletion tests partial | No authenticated UI check | NOT_LIVE_VERIFIED |
| Backups and monitoring | Yes | Yes | Security settings/status partial | Yes | Backup health tests | Public root health misroutes | PARTIAL |

## Known UX Stabilization Completed

- Current Sale/cart now uses a stable fixed-height panel, a dedicated scrollable cart-list region, no horizontal item overflow, and constrained long product names.
- Product editing now states that product changes do not change stock quantity and provides `Open Stock Adjustment`.
- Direct stock-edit messaging now explains transaction-controlled stock and points to the correction workflow.
- Product delete blockers now show stock, variant, inventory, sales, and purchase dependency counts with safe actions: correct stock, archive product, or view history.
- Product payload construction now explicitly normalizes optional UUID, decimal, and barcode fields before API submission.
- Barcode onboarding payload builders now guard against missing category/brand IDs before making a request.

## Contract Notes

- Product edit payloads do not submit `current_stock` when editing an existing product.
- Optional UUID-like fields are normalized before product and barcode onboarding requests.
- Barcode values remain strings and are not converted to numbers, preserving leading zeroes.
- Monetary fields are normalized before product submission; backend Pydantic schemas still validate authoritative decimal constraints.
- Product update errors now map stock-field and UUID-style failures to user-facing messages instead of raw backend text.

## Required Next Verification

1. Add or enable Playwright for browser-level tests. The current frontend test stack is Vitest only.
2. Use a disposable owner/manager/staff test login for public smoke tests.
3. Run the live journeys against test data only:
   - product create/edit
   - opening stock
   - barcode assignment
   - new sale cart add/increment/complete
   - stock correction
4. Fix `/health/live` routing so public health checks return backend health JSON rather than the React app shell.
5. Re-run this matrix and mark individual modules `WORKING` only after deployed UI verification succeeds.
