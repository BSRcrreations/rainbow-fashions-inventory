export function parseTransferBarcodes(value: string): string[] {
  return value
    .split(/[\n,\s]+/)
    .map((barcode) => barcode.trim())
    .filter(Boolean);
}

export function hasDuplicateBarcodes(barcodes: string[]): boolean {
  return new Set(barcodes.map((barcode) => barcode.toLowerCase())).size !== barcodes.length;
}

export function variantTransferLabel(variant: { size?: string | null; color?: string | null; style_code?: string | null }) {
  return [variant.size, variant.color, variant.style_code].filter(Boolean).join(" / ") || "Standard";
}

export function canConfirmBarcodeTransfer(value: string, phrase = "MOVE TO S"): boolean {
  return value.trim() === phrase;
}

export function barcodeTransferErrorMessage(cause: unknown): string {
  const maybe = cause as { code?: string; message?: string } | null;
  if (maybe?.code === "BARCODE_USED_IN_COMPLETED_SALE") return "One or more barcodes were used in a completed sale and cannot be transferred here.";
  if (maybe?.code === "BARCODE_TARGET_PRODUCT_MISMATCH") return "Select the S variant from the same product.";
  if (maybe?.code === "BARCODE_NOT_FOUND") return "One or more barcodes are not assigned in this store.";
  if (maybe?.code === "BARCODE_TRANSFER_CONFIRMATION_REQUIRED") return "Type MOVE TO S to confirm this transfer.";
  return cause instanceof Error ? cause.message : maybe?.message ?? "Unable to transfer these barcodes.";
}
