# UAT Checklist

Environment: isolated `rainbow_inventory_test` only. This checklist records the
2026-08-03 run; a blank result means it was deliberately not claimed as passed.

| Test ID | Feature | Preconditions / role | Steps | Expected result | Actual result | Pass / fail | Evidence / request ID | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UAT-001 | Owner login | Isolated owner account | Sign in at `/login` | Protected dashboard opens | UAT Owner and role rendered | PASS | Browser session | Valid `example.com` UAT email required |
| UAT-002 | Product rename | Owner, UAT product with stock | Edit Prisma product; change name; save; refresh | Metadata persists; stock cannot be edited in form | `Full Leggings UAT Verified` persisted, stock remained disabled | PASS | Product page refresh | Correct stock-edit UX |
| UAT-003 | Variant visibility | Owner, seeded six-size product | Open product in New Sale | Exact sizes, colour, SKU and barcode are selectable | M/Assorted variant displayed and selected | PASS | New Sale browser DOM | Uses exact variant identity |
| UAT-004 | Cart visibility | Owner, selected M variant | Add variant to cart | Visible cart line and stock-after-sale hint | 1 visible line, 1 unit, 20 to 19 hint | PASS | New Sale browser DOM | Prior hidden-cart issue not reproduced |
| UAT-005 | Percentage discount | Owner, one cart line | Press 10% | Total reflects percentage discount | INR 499.00 became INR 449.10 | PASS | New Sale browser DOM | Fixed discount not tested |
| UAT-006 | Sale completion | Owner, discounted cart | Complete sale; open history | Invoice, exact stock deduction, and history record persist | Invoice `RF-20260803-318796`; Prisma stock 120 to 119 | PASS | Sales History browser DOM | Isolated UAT mutation only |
| UAT-007 | Repeated barcode scan | Owner, known UAT manufacturer barcode | Scan same barcode twice | One review row; quantity and base pieces become 2 | One row, 2 scans, 2 pieces | PASS | Stock Scan browser DOM | No duplicate error |
| UAT-008 | Stock confirmation | Owner, staged repeated scan | Review and confirm | Append-only movement posts once and session locks | M stock 19 to 21; confirmed session locked | PASS | Stock Scan browser DOM | Isolated UAT mutation only |
| UAT-009 | Stock adjustment | Owner | Select exact variant and adjust | Ledger movement and audit event | Not run | NOT RUN | N/A | Requires separate fixture reset |
| UAT-010 | Stock reset | Owner | Preview, confirm reset, refresh | Products/variants/barcodes preserved; audited reversal | Not run | NOT RUN | N/A | Destructive path not run in this pass |
| UAT-011 | Category-first stock entry | Owner | Choose category, then brand, then scan | Brand list constrained to category | Not run | NOT RUN | N/A | UI present; workflow pending |
| UAT-012 | Cross-store access | Two stores, owner/staff/cashier | Attempt cross-store endpoints | 403/404 without leakage | Not run | NOT RUN | N/A | Add isolated second-store fixture |
| UAT-013 | Backup job visibility | Owner, configured backup test service | Open security/data-protection status | Recent job, retention, failure status visible | Not run | NOT RUN | N/A | Production blocker |
| UAT-014 | Suppliers | Owner, seeded ARK/GGl suppliers | Open `/suppliers` | Supplier totals and seeded suppliers render without API error | ARK distributors and GGl rendered | PASS | Browser UAT + authenticated API | Payment form visible; edit/delete not run |
| UAT-015 | Customers | Owner, seeded customers | Open `/customers` | Customer totals and seeded customers render without API error | Asha Retail Customer and Meena Credit Customer rendered | PASS | Browser UAT + authenticated API | Credit sale creation not run |
| UAT-016 | Expenses | Owner, seeded rent expense | Open `/expenses` | Expense categories and seeded expense render without API error | Rent and UAT monthly rent rendered | PASS | Browser UAT + authenticated API | Edit/delete not run |
| UAT-017 | Reports | Owner, seeded expense/sales/inventory data | Open `/reports` | P&L, cash flow, and inventory valuation render | Profit and loss and inventory valuation rendered | PASS | Browser UAT + authenticated API | Export/report drilldowns not implemented |
| UAT-018 | Mobile Business nav | Owner, 390px viewport | Open menu and Business links | Suppliers, Customers, Expenses, Reports are available | Mobile menu exposed all four links | PASS | Browser viewport UAT | Android-sized responsive smoke only |

Use a new UAT row for every repeat run. Do not reuse invoice numbers or request
IDs as proof after resetting the test database.
