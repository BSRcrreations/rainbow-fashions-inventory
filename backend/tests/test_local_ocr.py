from __future__ import annotations

from pathlib import Path

import pytest
from reportlab.pdfgen import canvas

from app.ai.base import OCRProcessingError
from app.ai.local_ocr import LocalOCRService


def test_local_ocr_reads_text_pdf(tmp_path: Path) -> None:
    invoice = tmp_path / "invoice.pdf"
    document = canvas.Canvas(str(invoice))
    document.drawString(72, 720, "Supplier: Divya Sri Textiles")
    document.drawString(72, 700, "Invoice Number: DS/26-27/05")
    document.save()

    text = LocalOCRService().extract_text(invoice)

    assert "Divya Sri Textiles" in text
    assert "DS/26-27/05" in text


def test_local_ocr_returns_safe_error_for_corrupt_pdf(tmp_path: Path) -> None:
    invoice = tmp_path / "broken.pdf"
    invoice.write_bytes(b"%PDF-not-a-valid-document")

    with pytest.raises(OCRProcessingError, match="could not be opened") as failure:
        LocalOCRService().extract_text(invoice)

    assert failure.value.code == "CORRUPTED_FILE"
