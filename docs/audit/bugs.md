# Bugs Fixed

- Category and brand delete operations could hard-delete records still referenced by products.
- Category and brand forms did not support edit, search, confirmation, toasts, loading skeletons, or empty states.
- Whitespace-only catalog names were not normalized before validation.
- API errors returned mixed detail formats that were harder for the frontend to display consistently.
- Frontend user role type omitted `MANAGER`.
- Product duplicate checks were case-sensitive for variants and barcodes.
- Product module lacked edit UX, filters, image upload, active/inactive control, and delete confirmation.
- Dashboard showed only plain loading text and did not show empty states for summary lists.
- Purchases had minimal feedback around upload/confirm failures and did not allow editing purchase price in review.
- Stock history lacked filters and CSV export in Stage 1 UI/API.
- Stock adjustment UI did not pre-validate negative-stock decreases.
