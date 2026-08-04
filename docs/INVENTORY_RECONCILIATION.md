# Inventory reconciliation

`ProductVariant.current_stock` is the authoritative sellable-stock quantity. `ProductInventory.current_stock` is the per-store compatibility aggregate and `Product.current_stock` is the legacy product aggregate. Cost-lot `remaining_quantity` is the available cost allocation quantity.

Owners and managers can use **Stock → Inventory Integrity** or `python -m scripts.reconcile_inventory --user-id <uuid>` to run a read-only report. Findings include healthy records, aggregate mismatches, cost-lot shortage/excess, negative stock, and products without sellable variants.

Only owners may preview and repair `PRODUCT_AGGREGATE_MISMATCH` or `STORE_INVENTORY_MISMATCH`. They must type `REPAIR INVENTORY AGGREGATES`, provide an idempotency key, and pass the production backup gate. Repairs lock the selected products, derive both compatibility values from variant totals, create immutable audit evidence, and never alter stock history or fabricate/edit cost lots.

Cost-lot discrepancies, negative stock, barcode conflicts, and historical movement concerns require a separately approved correction procedure. Do not edit database rows directly.
