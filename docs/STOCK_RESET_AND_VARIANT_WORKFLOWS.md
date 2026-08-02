# Stock Reset And Variant Workflows

## Purpose

Rainbow Fashions now manages inventory at the exact product variant level. A variant represents the sellable size, colour, barcode/SKU, price, and stock row for a base product. Base products remain grouped for browsing, but stock entry, stock correction, sale checkout, and reset actions operate on `product_variant_id`.

## Safe Existing-Stock Reset

The owner-only reset workflow is designed to remove earlier manually entered stock without deleting catalog data.

Flow:

1. Owner opens Stock and chooses **Reset Existing Stock to Zero**.
2. Owner selects a scope: selected variants, category, brand, product, all opening stock, or all current stock.
3. The backend generates a preview from the current variant balances.
4. The owner confirms the safety message and enters the configured deletion/security password when enabled.
5. The frontend sends the preview `request_id` as the `Idempotency-Key`.
6. The backend locks affected variants, records `STOCK_RESET_OUT` stock movements, writes audit events, zeroes variant and store inventory balances, and commits atomically.

The reset never deletes:

- products
- categories
- brands
- product variants
- barcode mappings
- previous stock history

## API Endpoints

`POST /api/v1/stock/reset-preview`

Creates a reset preview. Requires `OWNER`.

Request body:

```json
{
  "scope": "SELECTED_VARIANTS",
  "variant_ids": ["variant-uuid"],
  "category_id": null,
  "brand_id": null,
  "product_id": null
}
```

`POST /api/v1/stock/reset`

Confirms a reset. Requires `OWNER` and an `Idempotency-Key` header.

Request body:

```json
{
  "scope": "SELECTED_VARIANTS",
  "variant_ids": ["variant-uuid"],
  "confirmation_text": "This will set the selected existing stock quantities to zero. Products, variants and barcodes will remain available.",
  "owner_password": "optional-security-password"
}
```

## Stock Corrections

Stock corrections use exact variants and inventory transactions. The frontend posts `product_variant_id` with one of:

- `ADD_STOCK`
- `REMOVE_STOCK`
- `SET_COUNTED_QUANTITY`

For counted stock, the backend calculates the delta and records either an inbound or outbound adjustment movement. It does not directly assign a stock number without a ledger entry.

## Product Page

Products are shown as grouped base rows. Each base row expands to display:

- size
- colour
- barcode
- SKU
- MRP
- selling price
- cost
- exact stock
- active status

The base product stock equals the sum of its variants.

## Stock Entry

The scan-and-add workflow supports category and brand defaults before barcode entry. Known barcodes resolve to exact variants and repeated scans increment staged quantity. Permanent stock is updated only after confirmation.

## New Sale

New Sale keeps grouped base-product cards for fast browsing. Selecting a product opens exact variants so the cashier chooses the correct size/colour/barcode row. Cart lines and backend sale requests use `product_variant_id`.
