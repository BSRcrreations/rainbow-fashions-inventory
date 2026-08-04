# Barcode patch retirement audit

This audit reviewed the complete former `apply_barcode_feature.py` source mutator
before its retirement. Every intended behavior is implemented in maintained
application code; no runtime source replacement is required.

| Patch feature | Current implementation | Test evidence | Status |
| --- | --- | --- | --- |
| Product date persistence | `backend/alembic/versions/20260727_0012_product_date_barcode_scan.py`, product model and schema | `backend/tests/test_stage1_validation.py` | COMPLETE |
| Barcode generation | `backend/app/services/product_service.py` | `backend/tests/test_stage1_validation.py` | COMPLETE |
| Exact barcode lookup | `backend/app/services/sale_service.py`, product-variant barcode routes | `backend/tests/test_batch_barcodes.py` | REPLACED |
| Barcode label rendering | `frontend/src/components/BarcodeLabelDialog.tsx` | `frontend/src/components/BatchBarcodeDialog.test.ts` and product UI coverage | COMPLETE |
| POS barcode scanning | `frontend/src/pages/NewSalePage.tsx`, `backend/app/api/routes/sales.py` | `frontend/src/pages/NewSalePage.test.tsx` | REPLACED |
| Database migration | Alembic revisions 0012, 0022–0028 | `alembic heads` and migration history | COMPLETE |
| Product barcode API | `backend/app/api/routes/products.py`, `backend/app/api/routes/stock_scan.py` | `backend/tests/test_stage1_validation.py` | COMPLETE |
| Frontend types and product form | `frontend/src/types/index.ts`, `frontend/src/pages/ProductsPage.tsx` | frontend typecheck and build | COMPLETE |
| Import/export barcode and date fields | `backend/app/services/product_service.py` | `backend/tests/test_stage1_validation.py` | COMPLETE |
| Backup-directory behavior | No application behavior required; it was local patch-script backup only | `.gitignore` now excludes `.barcode-feature-backup/` | REPLACED |

No missing behavior was found. Other one-time source mutation scripts should be
reviewed independently; this retirement removes only the barcode patch script.
