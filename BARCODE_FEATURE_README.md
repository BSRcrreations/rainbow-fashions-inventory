# Rainbow Fashions barcode feature patch

This patch adds the requested workflow:

1. Create or generate a unique barcode for a product.
2. Enter a required **Product date**.
3. Use **Save & print** to save the product and open a printable 50 mm × 30 mm Code 128 label.
4. In **New Sale**, scan the barcode with a USB scanner. The scanner's Enter key performs an exact lookup, displays product details, and adds the product to the cart.

## Apply

```bash
cd "/Users/subbu/Documents/shop inventory"
python3 /path/to/apply_barcode_feature.py .
```

The script creates backups under:

```text
.barcode-feature-backup/<timestamp>/
```

## Migrate and validate

Use your normal backend environment. For a local Python environment:

```bash
cd "/Users/subbu/Documents/shop inventory/backend"
alembic upgrade head
python -m compileall app

cd ../frontend
npm run typecheck
npm run build
```

For Docker Compose, run Alembic inside the backend service instead, for example:

```bash
docker compose exec backend alembic upgrade head
```

## Test

1. Open **Products → New product**.
2. Fill product details and select **Product date**.
3. Click the wand beside Barcode, or leave Barcode blank to let the server generate one automatically.
4. Click **Save & print** and print the label.
5. Open **Sales → New Sale** and keep focus in the scan field.
6. Scan the label. Product name, size, colour, date, price, stock, and barcode should display; the product should also enter the cart.

## Files changed by the patch

- `backend/app/models/product.py`
- `backend/app/schemas/product.py`
- `backend/app/repositories/product.py`
- `backend/app/services/product_service.py`
- `backend/app/api/routes/products.py`
- `backend/alembic/versions/20260727_0010_product_date_barcode_scan.py`
- `frontend/src/types/index.ts`
- `frontend/src/components/BarcodeLabelDialog.tsx`
- `frontend/src/pages/ProductsPage.tsx`
- `frontend/src/pages/NewSalePage.tsx`

No new npm package is required; the label component renders Code 128-B directly as SVG.
