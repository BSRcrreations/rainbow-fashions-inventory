from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional

from app.schemas.purchase import ExtractedInvoice, ExtractedInvoiceItem


class InvoiceParser:
    def parse(self, raw_text: str) -> ExtractedInvoice:
        supplier = self._read_header(raw_text, "Supplier")
        invoice_number = self._read_header(raw_text, "Invoice Number")
        invoice_date = self._parse_date(self._read_header(raw_text, "Date"))
        total_amount = self._parse_decimal(self._read_header(raw_text, "Total")) or Decimal("0")
        items = self._parse_items(raw_text)
        if not total_amount and items:
            total_amount = sum((item.total_amount for item in items), Decimal("0"))
        return ExtractedInvoice(
            supplier=supplier,
            invoice_number=invoice_number,
            date=invoice_date,
            total_amount=total_amount,
            items=items,
        )

    def _read_header(self, raw_text: str, label: str) -> Optional[str]:
        prefix = f"{label}:"
        for line in raw_text.splitlines():
            if line.strip().lower().startswith(prefix.lower()):
                value = line.split(":", 1)[1].strip()
                return value or None
        return None

    def _parse_items(self, raw_text: str) -> list[ExtractedInvoiceItem]:
        items: list[ExtractedInvoiceItem] = []
        for line in raw_text.splitlines():
            if "|" not in line:
                continue
            parts = [part.strip() for part in line.split("|")]
            if len(parts) != 9:
                continue
            brand, category, name, size, color, qty, purchase_price, mrp, total = parts
            quantity = int(qty)
            items.append(
                ExtractedInvoiceItem(
                    brand=brand,
                    category=category,
                    product_name=name,
                    size=size,
                    color=color,
                    quantity=quantity,
                    purchase_price=self._parse_decimal(purchase_price) or Decimal("0"),
                    mrp=self._parse_decimal(mrp),
                    total_amount=self._parse_decimal(total) or Decimal("0"),
                    confidence=Decimal("0.9000"),
                )
            )
        return items

    def _parse_decimal(self, value: Optional[str]) -> Optional[Decimal]:
        if not value:
            return None
        try:
            return Decimal(value.replace(",", "").strip())
        except InvalidOperation:
            return None

    def _parse_date(self, value: Optional[str]) -> Optional[date]:
        if not value:
            return None
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            return None
