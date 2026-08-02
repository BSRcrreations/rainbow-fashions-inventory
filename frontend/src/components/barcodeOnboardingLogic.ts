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
