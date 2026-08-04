# Opening-stock import runbook

The opening-stock importer is an owner-only, audited setup tool. It accepts CSV or single-sheet XLSX files of at most 20,000 non-empty data rows and will not post a partial file.

## Before uploading

1. Take and verify a database backup through the operational backup workflow. The owner security screen must report the database component as `success`.
2. Download or copy the CSV template at `docs/templates/opening-stock-import-template.csv`.
3. Keep the required headers exactly as shown: `product_name`, `category`, `subcategory`, `brand`, `sku`, `barcode`, `quantity`, `purchase_cost`, and `selling_price`.
4. Use plain values only. Formulas, duplicate/missing headers, invalid quantities, invalid money values, duplicate SKU/barcode identities, and unsafe control characters block the whole import.

## Lifecycle and reconciliation

1. Upload in **Stock → Opening Stock Import**. The original file is retained in the configured runtime evidence directory, never in Git.
2. Review every validation error. The preview shows the first 100 rows; the API retains each row and error for complete audit evidence.
3. When the preview has no errors and backup evidence is current, type `POST OPENING STOCK` exactly. Supply a unique idempotency key through the API client; the web page generates one automatically.
4. Posting runs as a single transaction. It creates missing catalog hierarchy/products/variants/barcodes where valid, then cost lots, `OPENING_STOCK` movements, variant stock, product stock, and store product inventory.
5. Reconcile the completion report totals with the source file: valid rows, pieces, total cost, total retail value, cost lots, and stock movements must agree. Export stock history if an external audit record is required.

## Safe rollback

An owner may reverse an import only by typing `REVERSE OPENING STOCK` and providing a reason. Automatic reversal is intentionally blocked if any later stock movement exists for an affected variant, if stock is already lower than the imported quantity, or if import evidence is incomplete. In those cases, stop and use an approved, separately audited stock-correction process; do not edit tables or delete movements.

## Operations

Set `OPENING_STOCK_IMPORT_DIR` to a host-mounted directory outside the application release checkout and restrict it to the service account. Do not serve it over HTTP. `ALLOW_TEST_OPENING_STOCK_IMPORT_BYPASS` is only honored in a `test` environment and must remain false elsewhere.
