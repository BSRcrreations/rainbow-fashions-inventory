export type OnboardingAction = "EXISTING_VARIANT" | "NEW_VARIANT" | "NEW_PRODUCT";

export interface BarcodeOnboardingFormState {
  product_name: string;
  category_id: string;
  subcategory_id: string;
  brand_id: string;
  product_code: string;
  style_code: string;
  manufacturer_sku: string;
  internal_sku: string;
  size: string;
  color: string;
  hsn_sac: string;
  quantity: string;
  package_quantity: string;
  scan_unit: string;
  inventory_unit: string;
  sale_mode: string;
  purchase_cost: string;
  mrp: string;
  selling_price: string;
  pricing_type: string;
  product_date: string;
  minimum_stock: string;
  description: string;
  alternate_barcode: string;
  package_barcode: string;
  package_barcode_quantity: string;
  image_url: string;
}

export type BarcodeOnboardingField =
  | "selected_product"
  | "selected_variant"
  | "product_name"
  | "category_id"
  | "brand_id"
  | "size"
  | "purchase_cost"
  | "selling_price"
  | "mrp"
  | "package_quantity"
  | "quantity";

export interface BarcodeOnboardingValidation {
  message: string;
  field?: BarcodeOnboardingField;
}

export interface ExistingVariantBarcodePayload {
  session_id: string;
  action: "EXISTING_VARIANT";
  barcode: string;
  product_variant_id: string;
  quantity: number;
}

/** Keep existing-variant assignment deliberately small and server-authoritative. */
export function existingVariantBarcodePayload(
  sessionId: string,
  barcode: string,
  productVariantId: string,
  quantity: number,
): ExistingVariantBarcodePayload {
  return {
    session_id: sessionId,
    action: "EXISTING_VARIANT",
    barcode,
    product_variant_id: productVariantId,
    quantity,
  };
}

export interface NewVariantBarcodePayload {
  session_id: string;
  action: "NEW_VARIANT";
  barcode: string;
  existing_product_id: string;
  size: string | null;
  color: string | null;
  style_code: string | null;
  manufacturer_sku: string | null;
  internal_sku: string | null;
  hsn_sac: string | null;
  quantity: number;
  package_quantity: number;
  scan_unit: string;
  inventory_unit: string;
  sale_mode: string;
  purchase_cost: number;
  mrp: number | null;
  selling_price: number;
  pricing_type: string;
  alternate_barcode: string | null;
  package_barcode: string | null;
  package_barcode_quantity: number;
}

export interface NewProductBarcodePayload {
  session_id: string;
  action: "NEW_PRODUCT";
  barcode: string;
  product_name: string;
  category_id: string;
  subcategory_id: string | null;
  brand_id: string;
  product_code: string | null;
  size: string | null;
  color: string | null;
  style_code: string | null;
  manufacturer_sku: string | null;
  internal_sku: string | null;
  hsn_sac: string | null;
  quantity: number;
  package_quantity: number;
  scan_unit: string;
  inventory_unit: string;
  sale_mode: string;
  purchase_cost: number;
  mrp: number | null;
  selling_price: number;
  pricing_type: string;
  product_date: string | null;
  minimum_stock: number;
  alternate_barcode: string | null;
  package_barcode: string | null;
  package_barcode_quantity: number;
  description: string | null;
  image_url: string | null;
}

export function optionalUuid(value: string | null | undefined): string | null {
  const normalized = value?.trim();
  return normalized ? normalized : null;
}

function optionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized ? normalized : null;
}

function positiveInt(value: string, fallback = 1): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

function nonNegativeInt(value: string, fallback = 0): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : fallback;
}

function requiredMoney(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : Number.NaN;
}

function optionalMoney(value: string): number | null {
  if (!value.trim()) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function commonNewVariantFields(form: BarcodeOnboardingFormState) {
  return {
    size: optionalText(form.size),
    color: optionalText(form.color),
    style_code: optionalText(form.style_code),
    manufacturer_sku: optionalText(form.manufacturer_sku),
    internal_sku: optionalText(form.internal_sku),
    hsn_sac: optionalText(form.hsn_sac),
    quantity: positiveInt(form.quantity),
    package_quantity: positiveInt(form.package_quantity),
    scan_unit: form.scan_unit,
    inventory_unit: form.inventory_unit,
    sale_mode: form.sale_mode,
    purchase_cost: requiredMoney(form.purchase_cost),
    mrp: optionalMoney(form.mrp),
    selling_price: requiredMoney(form.selling_price),
    pricing_type: form.pricing_type,
    alternate_barcode: optionalText(form.alternate_barcode),
    package_barcode: optionalText(form.package_barcode),
    package_barcode_quantity: positiveInt(form.package_barcode_quantity),
  };
}

export function newVariantBarcodePayload(
  sessionId: string,
  barcode: string,
  existingProductId: string,
  form: BarcodeOnboardingFormState,
): NewVariantBarcodePayload {
  return {
    session_id: sessionId,
    action: "NEW_VARIANT",
    barcode,
    existing_product_id: existingProductId,
    ...commonNewVariantFields(form),
  };
}

export function newProductBarcodePayload(
  sessionId: string,
  barcode: string,
  form: BarcodeOnboardingFormState,
): NewProductBarcodePayload {
  const categoryId = optionalUuid(form.category_id);
  const brandId = optionalUuid(form.brand_id);
  if (!categoryId) throw new Error("Select a category");
  if (!brandId) throw new Error("Select a brand");
  return {
    session_id: sessionId,
    action: "NEW_PRODUCT",
    barcode,
    product_name: form.product_name.trim(),
    category_id: categoryId,
    subcategory_id: optionalUuid(form.subcategory_id),
    brand_id: brandId,
    product_code: optionalText(form.product_code),
    product_date: optionalText(form.product_date),
    minimum_stock: nonNegativeInt(form.minimum_stock),
    description: optionalText(form.description),
    image_url: optionalText(form.image_url),
    ...commonNewVariantFields(form),
  };
}

export function validateBarcodeOnboarding(
  action: OnboardingAction,
  form: BarcodeOnboardingFormState,
  selectedProductId: string,
  selectedVariantId: string,
): BarcodeOnboardingValidation | null {
  const quantity = Number(form.quantity);
  if (!Number.isInteger(quantity) || quantity < 1) {
    return { message: "Enter a quantity of at least 1", field: "quantity" };
  }

  if (action === "EXISTING_VARIANT") {
    return selectedVariantId ? null : { message: "Select the exact existing variant", field: "selected_variant" };
  }

  if (action === "NEW_VARIANT" && !selectedProductId.trim()) {
    return { message: "Select the existing product for this new variant", field: "selected_product" };
  }

  if (action === "NEW_PRODUCT") {
    if (form.product_name.trim().length < 2) return { message: "Enter a product name", field: "product_name" };
    if (!optionalUuid(form.category_id)) return { message: "Select a category", field: "category_id" };
    if (!optionalUuid(form.brand_id)) return { message: "Select a brand or choose Unbranded", field: "brand_id" };
  }

  if (!form.size.trim() && !form.color.trim() && !form.style_code.trim() && !form.manufacturer_sku.trim()) {
    return { message: "Enter a size, colour, style, or manufacturer SKU for the variant", field: "size" };
  }

  const purchaseCost = requiredMoney(form.purchase_cost);
  if (!Number.isFinite(purchaseCost) || purchaseCost < 0) {
    return { message: "Enter opening/purchase cost when required", field: "purchase_cost" };
  }

  const sellingPrice = requiredMoney(form.selling_price);
  if (!Number.isFinite(sellingPrice) || sellingPrice < 0) {
    return { message: "Enter selling price", field: "selling_price" };
  }

  const mrp = optionalMoney(form.mrp);
  if (form.pricing_type === "MRP" && mrp === null) {
    return { message: "Enter MRP when using MRP pricing", field: "mrp" };
  }
  if (mrp !== null && sellingPrice > mrp) {
    return { message: "Selling price cannot be greater than MRP", field: "selling_price" };
  }
  const packageQuantity = Number(form.package_quantity);
  if (!Number.isInteger(packageQuantity) || packageQuantity < 1) {
    return { message: "Enter pieces per scan", field: "package_quantity" };
  }
  if (packageQuantity > 1 && form.scan_unit !== "PACK") {
    return { message: "Package quantities above one must use Pack as the scan unit", field: "package_quantity" };
  }

  return null;
}

const errorMessages: Record<string, string> = {
  BARCODE_ALREADY_ASSIGNED: "This barcode is already assigned to another product variant.",
  BRAND_REQUIRED: "Select a brand or choose Unbranded",
  CATEGORY_REQUIRED: "Select a category",
  EXISTING_PRODUCT_REQUIRED: "Select the existing product for this new variant",
  EXISTING_VARIANT_REQUIRED: "Select the exact existing variant",
  PRODUCT_REQUIRED: "Enter a product name",
  SESSION_ALREADY_CONFIRMED: "This stock session is confirmed and cannot be changed.",
  STOCK_SESSION_CONFIRMED: "This stock session is confirmed and cannot be changed.",
  VARIANT_ALREADY_EXISTS: "This variant already exists. Use Assign existing variant to add another barcode.",
};

export function barcodeOnboardingErrorMessage(cause: unknown): string {
  const maybe = cause as { code?: string; message?: string } | null;
  if (maybe?.code && errorMessages[maybe.code]) return errorMessages[maybe.code];
  const message = cause instanceof Error ? cause.message : maybe?.message ?? "Unable to save this barcode mapping";
  if (/valid UUID|invalid length|expected length 32|uuid/i.test(message)) {
    if (/brand_id/i.test(message)) return "Select a brand or choose Unbranded";
    if (/category_id/i.test(message)) return "Select a category";
    if (/product_variant_id/i.test(message)) return "Select the exact existing variant";
    if (/existing_product_id/i.test(message)) return "Select the existing product for this new variant";
    return "Select the required product, category, brand, or variant before saving.";
  }
  return message;
}
