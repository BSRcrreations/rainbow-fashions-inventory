export type SaleDiscountType = "PERCENTAGE" | "FIXED_AMOUNT";

export type SaleDiscountPreview = {
  valid: boolean;
  error: string;
  discountAmount: number;
  total: number;
};

// Checkout totals are only a live preview. The backend repeats this calculation
// using Decimal values from locked current prices before it commits the sale.
const currency = (value: number) => Math.round((value + Number.EPSILON) * 100) / 100;

export function previewSaleDiscount(subtotal: number, discountType: SaleDiscountType, rawValue: string): SaleDiscountPreview {
  const value = rawValue.trim();
  if (!/^\d+(?:\.\d{0,2})?$/.test(value)) return { valid: false, error: "Enter a valid discount value.", discountAmount: 0, total: currency(subtotal) };
  const discountValue = Number(value);
  if (!Number.isFinite(discountValue)) return { valid: false, error: "Enter a valid discount value.", discountAmount: 0, total: currency(subtotal) };
  if (discountType === "PERCENTAGE") {
    if (discountValue < 0 || discountValue > 100) return { valid: false, error: "Discount percentage must be between 0 and 100.", discountAmount: 0, total: currency(subtotal) };
    const discountAmount = currency(subtotal * discountValue / 100);
    return { valid: true, error: "", discountAmount, total: currency(subtotal - discountAmount) };
  }
  if (discountValue < 0 || discountValue > subtotal) return { valid: false, error: discountValue > subtotal ? "Discount amount cannot be greater than the subtotal." : "Discount amount cannot be negative.", discountAmount: 0, total: currency(subtotal) };
  const discountAmount = currency(discountValue);
  return { valid: true, error: "", discountAmount, total: currency(subtotal - discountAmount) };
}

export function saleDiscountLabel(discountType: SaleDiscountType, value: string) {
  return discountType === "PERCENTAGE" ? `Discount (${value || "0"}%)` : "Discount";
}
