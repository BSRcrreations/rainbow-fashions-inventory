# Rainbow Fashions operator guide

Use the test shop for training. A real shop's opening stock must wait until the release checklist is approved.

## Opening stock

1. The owner opens **Stock → Opening Stock Import** and downloads the sample CSV. Remove the example row and enter the shop's stock.
2. Enter one row for each exact product, size, colour and style. Give each variant a unique SKU. Keep barcodes as text, including leading zeros. Quantities must be whole numbers; prices must have at most two decimal places.
3. If a supplier barcode intentionally covers multiple sizes, tick the shared-barcode confirmation. The SKU and size must still identify each row uniquely. Never divide shared stock between sizes by guessing.
4. Upload CSV or XLSX. This creates a preview only. Review quantities, cost, selling and MRP values. Use Previous/Next for large files and Download errors to find corrections. Correct the source file and upload it again. Use **Check preview again** after resolving backup or product conflicts.
5. Confirm that Backup Status has recent successful database, uploads and offsite backups and recent successful database/uploads restore checks. The server checks these again when posting.
6. Start with a small representative pilot, including multiple sizes and shared barcodes. Type **POST OPENING STOCK** to post. If the connection fails, review and retry the same import; do not create another stock entry.
7. Check Stock History and Inventory Integrity, count the pilot physically, and get the owner's approval before importing the rest.
8. A posted import cannot be edited. The owner can expand **Reverse this opening stock**, enter a reason and type **REVERSE OPENING STOCK** only if no later stock activity prevents reversal. The original evidence remains.

The downloadable template contains these required columns: `product_name, category, subcategory, brand, sku, barcode, quantity, purchase_cost, selling_price`. Optional columns are `size, color, style_code, mrp, hsn_code, gst_rate, description, unit, warehouse`. Warehouse is descriptive; this release does not implement separate warehouse balances. The template is also in this folder as `opening-stock-template.csv`.

## Daily stock entry

Open **Quick Stock Entry**. Scan, search, or choose a category. Select the exact size, enter quantity, optionally enter purchase cost, then **Add to draft**. Repeat for other items. Review the pieces and press **Save Stock**, then confirm.

Drafts save on the same device and user account. Return to the page and choose **Continue** after an interruption. Added draft rows do not change stock until final confirmation. If confirmation is uncertain, keep the entry unchanged and retry **Save Stock**. Do not clear browser data or switch devices to recover a local draft. Quick Purchase photos also recover on the same account/device. Wait until the photo has saved before leaving the page. Browser storage must remain available.

Use Quick Purchase instead when supplier payment and purchase accounting must be recorded. Product editing is not a stock correction workflow.

## Quick Purchase

Open **Quick Purchase**. Choose a supplier or use Local Wholesale. Set the date. Search/scan, choose the exact size, enter quantity and cost, then add. Invoice number, selling price, payment, amount paid, notes and a photo are optional details. Check the supplier, quantities and total, then **Confirm Purchase**. The confirmed purchase adds exact-size stock, cost lots and stock history and updates the supplier account.

A photo attached to Quick Purchase is supporting evidence; it does not extract or post stock. Use the existing purchase-document upload/review workflow for OCR. Review every extracted item, map its exact size and check quantities and prices before confirming. OCR is an aid and does not bypass review. Text PDFs, scanned PDF pages and supported photos can be extracted locally. Always check the extracted invoice against the original; unclear values are highlighted. If extraction fails, attach the photo to a manually entered Quick Purchase.

## Billing

Open **New Sale**. Choose a category, scan a barcode, or search by product/brand/size. Select a size and add it to the cart. A shared barcode asks you to choose a size. Check size, quantity, available stock and price in the cart.

Open **Checkout**, optionally add customer information, choose Cash, UPI, Card, Bank, Other or Credit, and enter a reference when required. Credit needs a saved customer and available credit allowance. Item and bill discounts are checked together against the cashier's configured limit. Ask the manager to complete bills above that limit.

Confirm once. An uncertain result must be retried using **the original saved request**. After success, select **Print / Reprint Bill**. Reprinting does not create another sale or change stock. Billing details and the cart survive a refresh on the same account/device; completed bills clear the draft.

## Returns and exchanges

Find the original bill in Sales History and choose **Return / Exchange**, or search in the Returns page by invoice, customer/phone or date. Select quantities within the remaining returnable quantity and enter a reason. Keep **Good condition** checked only for sellable goods. Damaged returns refund the paid amount without increasing sellable stock.

For an exchange, also choose replacement sizes. Confirm the return and replacement together; the application reports the difference to collect/refund. The original discounts are included in refund calculations. Credit invoices must reduce the credit balance. For a credit exchange, keep Credit as the replacement payment method and use the same customer. The return reduces their balance before the replacement checks the available credit; both sides confirm together or neither is posted.

If a result is uncertain, use **Check original return / exchange** before another return. The original bill, return and stock evidence remain available. A manager can void a sale when appropriate; do not edit completed variant stock through an invoice editor.

## Purchase returns and supplier credit

A manager/owner opens **Purchase Returns**, finds the original confirmed purchase, selects return quantities and supplies a reason and optional credit-note reference. Confirm only goods that are leaving sellable stock. The application checks received quantities, previous returns, current exact-size stock and cost history. It records supplier credit separately from payments. Retry the original request if confirmation is uncertain.

## Day closing

After the day's transactions, open **Day Closing**. Choose the date, enter opening cash and the cash actually counted. Review cash sales, cash refunds, cash expenses, customer receipts and supplier cash payments. The difference shows shortage/excess. Add a note and save. A manager/owner checks and approves the report. Approved reports keep their original snapshot. Closing covers the whole shop by business date.

## Reports and low stock

Open **Reports** and choose Today, Yesterday, 7 days, 30 days or This month, or enter dates and press Apply. **Download all reports (Excel)** exports 15 sheets covering sales, recorded GST, returns, purchases, supplier credits, movements, inventory, low stock, expenses, day closing, payment modes and customer/supplier balances. Exports allow up to 366 days and 50,000 rows per sheet; narrow the dates if the server requests it. Current inventory and balances are snapshots at download time, not reconstructed period-end balances. Recorded GST amounts are invoice evidence, not a statutory tax filing.

Expand **Low stock by size** and filter by category, brand or supplier. Supplier filters use confirmed receipts. In **Products → Manage variant**, set **Minimum stock for this size**; leave it empty to inherit the product minimum. This changes the reorder threshold only. It does not add or remove stock.

## Printers

Open **Printer Settings**. Set Receipt Printer width to 80 mm or 58 mm, margins and copies. Set Label Printer dimensions, margins, copies and visible fields. Common labels include 50 × 30, 40 × 30 and 40 × 20 mm. Select GST display only after the owner has checked product tax data and the store's CGST/SGST or IGST setting. New bills retain recorded tax amounts; historical invoices are not retroactively assigned tax.

Use **Print test receipt** and **Print test label** to check alignment, then choose the correct connected device in the operating system's print dialog. Density and driver options are controlled there. Allow print pop-ups for the shop. Labels require an exact size selection for products with several variants and do not show purchase cost. No model-specific Bluetooth or SDK adapter is installed; browser/system printing is the supported path until a printer model is provided and tested.

## Users and permissions

| Role | Intended access |
|---|---|
| Owner | All operations, opening stock, security, backups, user administration and guarded destructive actions |
| Manager | Billing, returns, purchases, corrections, printer settings and closing approval |
| Cashier | Billing, customer operations, limited returns and closing submission |
| Stock staff | Product/stock work and purchase receiving |
| Accountant | Purchases, suppliers, expenses and financial reports |
| Viewer | Read-only screens permitted by server policy |

Create an individual account in **Users & Roles**. Use a strong password of at least 12 characters. Owners can change access or disable an account with a reason. The last active owner is protected. Old STAFF accounts retain compatibility; review their access before assigning the new roles. Password recovery/self-service reset is not added by this release.

## Stock corrections, integrity and backup status

Use the manager's Stock Adjustment/count workflow with a reason. If stock changed since a count began, review it again. Inventory Integrity compares recorded movements, exact-size stock, product/store totals and cost lots. An owner can repair eligible summary totals only with the required backup gate and confirmation. Investigate movement or cost-lot discrepancies; they are not automatically rewritten.

Backup Status is read-only operational evidence. A green local test result does not prove the production shop or its offsite copy is recoverable. Missing/stale evidence blocks opening-stock posting. Ask the operator responsible for the server to follow the release checklist.

## Formal purchase drafts

Open the invoice and choose Edit. Header details and all product rows are saved as an unfinished draft on this account/device as you work. Save draft writes the complete invoice together. Select each exact size, review quantities, costs, MRP, selling price, tax, discounts and payments, then Confirm and add stock. Uploading, extraction and Save draft do not post stock. If another employee changed the invoice, reload and review their saved version before saving again. When the result of a save is uncertain, use the original retry before making further edits.

## Four-stage real inventory pilot

Begin only after FINAL-CERTIFICATION.md blockers are cleared and the owner approves the release. Practice transactions in TEST first. Real records must represent actual goods and actual business events; do not create fictitious sales in production.

1. **10 representative products.** Include a unique barcode, a shared barcode family, several sizes and different costs/prices. Freeze movement of the pilot goods while physically counting. Enter one row per exact variant. A second person checks SKU, size, barcode, pieces and values. Preview, approve and post once. In TEST rehearse stock, sale, sellable/damaged return, M-to-L exchange, purchase and count correction against this shape of data. In the real pilot, record those actions only when they actually occur. Require physical count equality and zero unexplained reconciliation discrepancies before advancing.
2. **50–100 variants.** Import only new, unentered inventory. Exclude all Pilot 1 rows so goods are not counted twice. Recount every variant, compare cost/stock history and require zero unexplained discrepancies. Check staff can resume unfinished entry and retrieve an uncertain confirmation safely. Obtain owner sign-off.
3. **One complete category or brand.** Include only the remaining unentered variants. Reconcile any sales/receipts during counting to the agreed cutoff. Recount and require zero unexplained discrepancies; investigate every difference before advancing.
4. **Remaining full-shop opening inventory.** Import batches of at most 20,000 rows, excluding all earlier posted goods. Keep source files, import IDs and totals. A large confirmation may take several minutes: if a network timeout occurs, inspect/retry the same import; never upload a second copy to force it through. Confirm each batch, reconcile and physically verify before the next. Finish with whole-shop totals and owner approval.

At any stage, stop expansion if quantities, costs, backup status or recovery behavior is unexplained. Keep evidence and use the audited correction/reversal process; do not erase history or reset stock to make totals match.
