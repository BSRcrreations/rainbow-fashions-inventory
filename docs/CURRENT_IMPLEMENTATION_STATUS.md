# Current implementation status

This is the source-of-truth status for commit `54cf706`. “Tested” means covered
by the repository’s automated test suite; it does not assert production or UAT
verification.

| Module | Status | Evidence | Live verification |
| --- | --- | --- | --- |
| Authentication | Implemented and tested | auth routes, services, schemas, role enum | Pending |
| Categories, subcategories, brands | Implemented and tested | catalog routes/services and frontend catalog manager | Pending |
| Products, variants, barcodes | Implemented and tested | product/variant models, barcode APIs, barcode tests | Pending |
| Purchases and OCR documents | Implemented and tested | purchase routes/services, document job model, OCR tests | Pending |
| Stock scan and opening stock | Implemented and tested | stock-scan routes/services and barcode tests | Pending |
| Stock adjustment | Implemented and tested | stock service/routes and correction tests | Pending |
| Sales/POS | Implemented and tested | sales routes/service, POS and sale tests | Pending |
| Sale edits, returns, voids | Implemented and tested | sale service/audit models and destructive-action tests | Pending |
| Suppliers, customers, expenses, reports | Implemented and tested | business routes/services and frontend pages | Pending |
| Security settings | Implemented and tested | security route/service and deletion-security tests | Pending |
| Backup and restore | Implemented but live verification pending | deployment scripts, timers, status service | Required before production |
| Mobile | Scaffold only | Expo entry point and package manifest | Not production-ready |

## Operational facts

- Upload and OCR processing do **not** change stock.
- Purchase confirmation changes stock.
- Stock-scan confirmation changes stock.
- Sale checkout consumes variant stock and records stock history.
- Sale returns and voids use compensating stock movements.
- Product hierarchy is product → variant → barcode mapping.
- Owner-only destructive actions require the server-side destructive-action flow.

## Production blockers on this base

The safe one-time owner bootstrap command is not present in this branch. Do not
use published/default credentials. Merge the approved security bootstrap change
before production deployment, then create the first owner from protected
environment values or a hidden prompt. Real environment files and credentials
must never be committed.

Deployment requires protected environment setup, migration application, owner
bootstrap, service startup, health checks, and a tested backup/restore path.
