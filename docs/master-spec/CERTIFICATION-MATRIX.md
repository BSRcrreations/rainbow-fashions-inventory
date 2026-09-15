# Master requirement matrix

Final review: 15 September 2026. COMPLETE means the software requirement is implemented with the bounded local evidence in FINAL-CERTIFICATION.md; it is not production approval. External hardware, staff and live recovery acceptance are identified explicitly. All 55 original sections are represented below.

| § | Requirement | Status | Evidence / gap |
|---|---|---|---|
| 1 | Smartphone-style UX | EXTERNAL VERIFICATION REQUIRED | Dense existing screens → category buttons, simple quick flows, larger touch controls and plain status messages. Actual staff usability sign-off remains. |
| 2 | Global navigation | COMPLETE | Existing navigation → grouped role-filtered links for quick workflows, returns, operations and administration. |
| 3 | Category-first billing | COMPLETE | Category buttons, product/size selection and paged search retained and improved. Completed category, typed-barcode and search sales in local browsers; physical scanner acceptance is separate. |
| 4 | Product cards | COMPLETE | Existing cards retained and connected to paginated variants, price, availability and size selection. |
| 5 | Cart | COMPLETE | Existing cart → exact-size rows, quantity controls, item discounts and durable recovery. |
| 6 | Shared barcode | COMPLETE | Shared barcode never selects a size automatically. Six-size chooser tested in frontend and browser; database rejects ambiguous lookup. Exact-size selection used by sale, daily stock, quick/formal purchase and adjustment; opening imports require explicit row SKU/size and shared-family approval. |
| 7 | Product structure | COMPLETE | Existing product/variant model retained; transactions require exact variants and capture receipt attributes. |
| 8 | Opening import | COMPLETE | CSV/XLSX validation, preview, errors, totals, explicit shared families, atomic posting, cost lots, retry and restricted reversal tested. 20,000 rows posted in an isolated PostgreSQL database; repeated confirmation produced no duplicate stock; reconciliation healthy. |
| 9 | Opening import UX | COMPLETE | Six visible stages; downloadable template, paged review/errors, new/existing product counts, piece/cost/selling/MRP totals and shared warnings. Browser download/upload/preview passed; posted completion includes discrepancy check. |
| 10 | Initial inventory safety | COMPLETE | Historical automatic leggings seed → no-op for new installs; frozen schema baseline; no production stock changes or implicit opening posting. |
| 11 | Daily stock | COMPLETE | Large scanner workflow → dedicated Quick Stock Entry with absolute draft rows and final confirmation. |
| 12 | Interruption safety | COMPLETE | Weak local recovery → user/store-scoped drafts, stable document IDs, server retries and locked uncertain confirmations. |
| 13 | Small wholesale purchases | COMPLETE | Formal flow only → Quick Purchase with optional supplier/invoice/photo, quantity/cost entry and exact-size confirmation. |
| 14 | Photo purchase | COMPLETE | Photo attachment survives reload in Chromium/WebKit. Tesseract plus Poppler handles images and scanned PDF pages; HEIC is converted locally. Real synthetic PDF upload/extract/review materializes draft lines without stock changes. Low confidence is highlighted; manual photo attachment remains available if extraction fails. Shop invoice accuracy needs staff acceptance. |
| 15 | Purchase module | COMPLETE | Formal header and all lines save atomically with version/idempotency checks. Complete local editor draft recovery and exact-size picker added. Browser PDF upload, recovered edits, shared M selection and confirmation passed. Existing supplier/date/tax/discount/payment/attachment fields retained. |
| 16 | Supplier returns | COMPLETE | Missing → linked purchase return and credit note, quantity/stock/cost limits, idempotency and supplier ledger effects. |
| 17 | Customer returns/exchange | COMPLETE | Discounted partial and damaged returns, idempotent void, linked atomic exchange and rollback tests pass. Credit-to-credit exchanges reuse the same customer allowance atomically; a failed replacement rolls back the return. |
| 18 | Discounts | COMPLETE | Bill discount → item and bill discounts combined for cashier cap; owner/manager override and recorded receipt data. Real DB cap tests pass. |
| 19 | Payments | COMPLETE | Partial UI choices → Cash/UPI/Card/Bank/Other/Credit, reference policy, credit limit and credit-return balances. All noncredit methods tested in PostgreSQL. |
| 20 | Receipts | EXTERNAL VERIFICATION REQUIRED | Hard-coded bill → configurable 80/58 mm print document, store/contact/logo, size/brand, MRP, discount, savings, payment/reference and recorded GST breakdown. Physical output is unverified. |
| 21 | Labels | EXTERNAL VERIFICATION REQUIRED | Fixed 50×30 label → configurable dimensions/margins/copies/fields and exact variant selection. No purchase cost printed. Physical scan/alignment proof remains. |
| 22 | Printer integration | EXTERNAL VERIFICATION REQUIRED | Hard-coded popup → separate receipt/label settings, test printing and shared browser printer function. No device-specific adapter: no printer model/SDK was supplied. |
| 23 | Adjustments | COMPLETE | Exact variant is mandatory. Count-to-zero supported; movement and cost evidence updated atomically, original request retry changes stock once. Shared picker, reason, count review and uncertain-result recovery are available. |
| 24 | Integrity | COMPLETE | Aggregate checks → expected quantity from immutable movements, per-size differences and missing/arithmetic ledger findings; repair remains restricted to eligible summary totals. |
| 25 | Stock history | COMPLETE | Existing history preserved and connected to quick stock/purchases, sales, returns, exchanges and supplier returns. |
| 26 | Dashboard | COMPLETE | Simple sales/bills/pieces, Cash/UPI/Card/Bank/Credit, expenses, size-level low/out stock, supplier payable, customer receivable, current cost/retail inventory, discrepancy and owner backup cards. Store-scoped database regression covers accounts and net collections. |
| 27 | Closing/shift | COMPLETE | Whole-shop day closing records opening/actual cash, sales/refunds/customer and supplier cash payments, expenses, difference, all payment totals and manager/owner approval; immutable approved history. This satisfies the requested day-closing scope. |
| 28 | Customers | COMPLETE | Existing customer module retained; scoped credit limit and credit-return accounting added. |
| 29 | Suppliers | COMPLETE | Existing module → confirmed-only invoices and supplier credit-note accounting in balances/ledger. |
| 30 | Expenses | COMPLETE | Existing categories, expenses and date/report capabilities retained; role access aligned. |
| 31 | Reports | COMPLETE | Existing sales/P&L/valuation/movement/account screens retained; refund/cash corrections added. Date presets and a unified Excel download now include recorded GST, closing, returns, purchases, stock, expenses, payment modes and accounts. Current inventory/balances are explicitly distinguished from period activity. Statutory GST filing and historical tax reconstruction are outside this export. |
| 32 | Roles | COMPLETE | OWNER/MANAGER/STAFF → CASHIER/STOCK_STAFF/ACCOUNTANT/VIEWER with server dependencies, route filtering and owner user administration. Full hands-on role matrix remains. |
| 33 | Errors | COMPLETE | Raw errors in some paths → plain messages and optional diagnostic details; transaction errors do not clear drafts. |
| 34 | Autosave | COMPLETE | Cart/checkout, quick stock/purchase and every unsaved formal purchase field recover on the same device/account. Optional purchase photo bytes are stored in account/store-scoped IndexedDB; Chromium/WebKit recovery and upload passed. Clearing browser storage is not a supported recovery path. |
| 35 | Network UX | COMPLETE | Basic failure handling → offline notice, same-request retries and locked uncertain confirmations. Final inventory writes still require the server. |
| 36 | Database truth | COMPLETE | Preserved; local data represents drafts only. Confirmed quantities derive from server transactions and cost/history evidence. |
| 37 | Backup/recovery | EXTERNAL VERIFICATION REQUIRED | Existing scripts → freshness/restore/offsite posting gate and owner status screen; local restore verified. Production-specific offsite/media/alerts remain unverified. |
| 38 | Security | EXTERNAL VERIFICATION REQUIRED | Existing guards retained; dependency vulnerabilities removed, tenant queries hardened, secret scans passed. Actual server/TLS/firewall/OS-image review remains. |
| 39 | CI/CD | EXTERNAL VERIFICATION REQUIRED | Existing two-environment pipeline → mandatory PostgreSQL integration/concurrency and pip audit; full Alembic replay on empty deployments. Remote current-SHA run remains. |
| 40 | Fresh documentation | COMPLETE | Fresh 20-section certification, 55-section matrix, every changed-file purpose, source hashes and final evidence generated. The candidate is explicitly an uncommitted working tree; no claim that the base SHA contains changes. |
| 41 | Mobile/tablet | EXTERNAL VERIFICATION REQUIRED | Automated Chromium and WebKit workflows passed at desktop/tablet/phone widths. Actual Safari on the shop device, touch keyboard and staff acceptance remain external. |
| 42 | Hardware workflow | EXTERNAL VERIFICATION REQUIRED | Browser/system printing and scanner input available; actual connected scanner, printer, reconnect and drawer tests pending. |
| 43 | Barcode fallback | COMPLETE | Search/category/manual barcode entry retained; explicit size selection supports items without a scannable label. |
| 44 | Low stock | COMPLETE | Product minimums → optional per-size overrides, current low/out-of-stock report, category/brand/supplier filters and Excel sheet. Empty size minimum inherits its product setting; supplier filters use confirmed receipts. |
| 45 | Duplicates | COMPLETE | Transaction idempotency, stable drafts, locked confirmations and import identities added; real concurrent proofs pass. |
| 46 | Audit | COMPLETE | Multiple existing logs → combined store-scoped paged audit screen with actor/action/reason and sensitive-field filtering. No audit-delete UI/API added. |
| 47 | Product deletion | COMPLETE | Existing owner/password/history safeguards retained and tested. No real records deleted to pass tests. |
| 48 | Performance | PARTIAL | Paged catalog, lazy screens and bulk validation implemented. 20,000-row preview 2.66 seconds; full post 396.73 seconds, no duplicate on repeat and healthy reconciliation. Real server search/concurrency/HTTP timeout and operational-load acceptance remain unmeasured. |
| 49 | Accessibility | EXTERNAL VERIFICATION REQUIRED | Larger controls, text labels, visible keyboard focus and plain messages added; formal assistive-technology and elderly-user trial not performed. |
| 50 | Confirmations | COMPLETE | Explicit financial/stock confirmations and uncertain-state recovery; normal navigation does not ask approval. |
| 51 | Go-live matrix | EXTERNAL VERIFICATION REQUIRED | All local software gates recorded. Physical printing/scanning, offsite/alerts, production-clone migration and exact remote release verification remain unproven. See GO-LIVE-CHECKS.md. NO-GO. |
| 52 | Safe go-live | EXTERNAL VERIFICATION REQUIRED | Written pilot → reconciliation → physical count → owner approval → full import procedure. No real pilot/full import performed. |
| 53 | Development approach | COMPLETE | Existing repository audited/preserved, additive changes and real service/database evidence; no mock-only replacement site. |
| 54 | Tests | COMPLETE | Latest complete suites: 317 backend/deployment tests and 81 frontend tests. Lint/typecheck/build, dependency scans, concurrency, migrations, real OCR, capacity, backup/restore and both browser engines executed; exact evidence and limits recorded. |
| 55 | Deliverables | COMPLETE | All requested reporting artifacts delivered: full certification, before/after matrix, changed-file purposes and hashes, evidence, template, shop guides, four-stage inventory pilot, activation/rollback checklist and explicit NO-GO decision. |
