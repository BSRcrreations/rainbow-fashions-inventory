import type { PurchaseItem } from "../types";

type PurchaseDiscountType = NonNullable<PurchaseItem["discount_type"]>;

export interface PurchaseLinePreview {
  chargeableQuantity: string;
  freeQuantity: string;
  receivedQuantity: string;
  grossAmount: string;
  itemDiscount: string;
  taxableAmount: string;
  taxAmount: string;
  lineTotal: string;
  netUnitPrice: string;
  effectiveUnitCost: string;
}

const PERCENT_SCALE = 1_000_000n; // 100% stored with four decimal percentage places.

function decimal(value: string | number | null | undefined, scale: number): bigint {
  const text = String(value ?? "0").trim();
  if (!/^\d*(?:\.\d*)?$/.test(text) || !text) return 0n;
  const [whole = "0", fraction = ""] = text.split(".");
  const padded = `${fraction}${"0".repeat(scale)}`.slice(0, scale);
  return BigInt(whole || "0") * 10n ** BigInt(scale) + BigInt(padded || "0");
}

function format(value: bigint, scale: number): string {
  const sign = value < 0n ? "-" : "";
  const absolute = value < 0n ? -value : value;
  const divider = 10n ** BigInt(scale);
  const whole = absolute / divider;
  const fraction = (absolute % divider).toString().padStart(scale, "0");
  return scale === 0 ? `${sign}${whole}` : `${sign}${whole}.${fraction}`;
}

function divideRounded(numerator: bigint, denominator: bigint): bigint {
  if (denominator === 0n) return 0n;
  return (numerator + denominator / 2n) / denominator;
}

function moneyCents(value: string | number | null | undefined): bigint { return decimal(value, 2); }
function quantity(value: string | number | null | undefined): bigint { return decimal(value, 0); }
function percentage(value: string | number | null | undefined): bigint { return decimal(value, 4); }
function currency(value: bigint): string { return format(value, 2); }

export function addMoney(...values: Array<string | number | null | undefined>): string {
  return currency(values.reduce((total, value) => total + moneyCents(value), 0n));
}

export function subtractMoney(amount: string | number | null | undefined, discount: string | number | null | undefined): string {
  return currency(moneyCents(amount) - moneyCents(discount));
}

export function addQuantity(...values: Array<string | number | null | undefined>): string {
  return format(values.reduce((total, value) => total + quantity(value), 0n), 0);
}

export function previewPurchaseLine(item: PurchaseItem): PurchaseLinePreview {
  const chargeableQuantity = quantity(item.chargeable_quantity ?? item.quantity);
  const freeQuantity = quantity(item.free_quantity);
  const listUnitPrice = moneyCents(item.list_unit_price ?? item.purchase_price);
  const grossAmount = chargeableQuantity * listUnitPrice;
  const type: PurchaseDiscountType = item.discount_type ?? "NONE";
  let itemDiscount = 0n;

  if (type === "PERCENTAGE") itemDiscount = divideRounded(grossAmount * percentage(item.discount_percentage), PERCENT_SCALE);
  if (type === "FIXED_PER_UNIT") itemDiscount = chargeableQuantity * moneyCents(item.discount_per_unit);
  if (type === "FIXED_PER_LINE" || type === "MANUAL") itemDiscount = moneyCents(item.discount_amount ?? item.discount);
  if (type === "FINAL_UNIT_PRICE") itemDiscount = chargeableQuantity * (listUnitPrice - moneyCents(item.invoiced_unit_price));
  itemDiscount = itemDiscount < 0n ? 0n : itemDiscount > grossAmount ? grossAmount : itemDiscount;

  const taxableAmount = grossAmount - itemDiscount;
  const taxAmount = divideRounded(taxableAmount * percentage(item.tax_rate), PERCENT_SCALE);
  const receivedQuantity = chargeableQuantity + freeQuantity;
  return {
    chargeableQuantity: format(chargeableQuantity, 0),
    freeQuantity: format(freeQuantity, 0),
    receivedQuantity: format(receivedQuantity, 0),
    grossAmount: currency(grossAmount),
    itemDiscount: currency(itemDiscount),
    taxableAmount: currency(taxableAmount),
    taxAmount: currency(taxAmount),
    lineTotal: currency(taxableAmount + taxAmount),
    netUnitPrice: chargeableQuantity ? currency(divideRounded(taxableAmount, chargeableQuantity)) : "0.00",
    effectiveUnitCost: receivedQuantity ? currency(divideRounded(taxableAmount, receivedQuantity)) : "0.00",
  };
}

export function previewInvoiceDiscount(
  type: string | undefined,
  percentageValue: string | undefined,
  amount: string | undefined,
  eligibleAmount: string,
): string {
  if (!type || type === "NONE") return "0.00";
  const eligible = moneyCents(eligibleAmount);
  const requested = type === "PERCENTAGE"
    ? divideRounded(eligible * percentage(percentageValue), PERCENT_SCALE)
    : moneyCents(amount);
  return currency(requested > eligible ? eligible : requested);
}
