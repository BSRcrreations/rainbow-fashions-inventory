export function normalizeOptionalUuid(value: string | null | undefined) {
  const normalized = value?.trim();
  return normalized ? normalized : null;
}

export function normalizeBarcode(value: string | null | undefined) {
  const normalized = value?.trim();
  return normalized ? normalized : null;
}

export function normalizeDecimal(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") return null;
  const amount = typeof value === "number" ? value : Number(value);
  return Number.isFinite(amount) ? amount : null;
}

export function friendlyFieldError(message: string) {
  if (/category_id|category/i.test(message)) return "Select a category.";
  if (/subcategory_id|subcategory/i.test(message)) return "Select a subcategory.";
  if (/brand_id|brand/i.test(message)) return "Select a brand.";
  if (/uuid|valid uuid|invalid uuid|length/i.test(message)) return "Select a valid saved record before continuing.";
  if (/barcode/i.test(message)) return "Check the barcode and try again.";
  return message;
}
