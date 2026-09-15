import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

export type ReceiptSettings = { printer_type: "BROWSER"; width_mm: 80 | 58; margin_mm: number; copies: number; show_gst: boolean; tax_mode?: "INTRA_STATE" | "INTER_STATE"; return_policy: string; thank_you: string };
export type LabelSettings = { printer_type: "BROWSER"; width_mm: number; height_mm: number; margin_mm: number; copies: number; show_product_name: boolean; show_size: boolean; show_mrp: boolean; show_barcode_number: boolean };
export type StoreSettings = { name: string; address: string; phone: string; gstin: string; logo_url: string; timezone: string; cashier_max_discount_percent: string; require_payment_reference: boolean; receipt: ReceiptSettings; label: LabelSettings };

export function useStoreSettings() {
  return useQuery({ queryKey: ["store-settings"], queryFn: () => api.get<StoreSettings>("/settings/store"), staleTime: 60_000 });
}
