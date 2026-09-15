import type { Customer } from "../types";

export function normalizePhone(value: string) {
  let digits = value.replace(/\D/g, "");
  if (digits.startsWith("00")) digits = digits.slice(2);
  if (digits.length === 12 && digits.startsWith("91")) digits = digits.slice(2);
  return digits;
}

export function isCurrentCustomerLookup(customerPhone: string, lookupPhone: string) {
  const normalizedCustomerPhone = normalizePhone(customerPhone);
  return normalizedCustomerPhone.length >= 8 && normalizedCustomerPhone === normalizePhone(lookupPhone);
}

export function checkoutCustomerPayload({ customerPhone, customerName, customerDetails, lookupPhone, lookupCustomer }: { customerPhone: string; customerName: string; customerDetails: string; lookupPhone: string; lookupCustomer: Customer | null }) {
  // A query response is only safe to use when it belongs to the phone currently
  // displayed in the checkout form. Never carry an older customer across a
  // debounced phone change.
  const matchedCustomer = isCurrentCustomerLookup(customerPhone, lookupPhone) ? lookupCustomer : null;
  const loadedCustomerDetails = matchedCustomer ? [matchedCustomer.address, matchedCustomer.notes, [matchedCustomer.city, matchedCustomer.state, matchedCustomer.postal_code].filter(Boolean).join(", ")].filter(Boolean).join("\n") : "";
  return {
    customer_id: matchedCustomer?.id ?? null,
    customer_name: customerName.trim() || matchedCustomer?.name || null,
    customer_phone: normalizePhone(customerPhone) || null,
    customer_details: customerDetails.trim() || loadedCustomerDetails || null,
  };
}
