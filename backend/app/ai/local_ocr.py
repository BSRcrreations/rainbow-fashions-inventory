from __future__ import annotations

import subprocess
from pathlib import Path

from pypdf import PdfReader

from app.ai.base import OCRProcessingError, OCRService
from app.core.config import get_settings


class LocalOCRService(OCRService):
    """Read text-based PDFs directly and send supported images to local Tesseract."""

    def extract_text(self, file_path: Path) -> str:
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            return self._extract_pdf_text(file_path)
        if suffix in {".jpg", ".jpeg", ".png", ".webp"}:
            return self._run_tesseract(file_path)
        raise OCRProcessingError("UNSUPPORTED_FILE_TYPE", "This invoice format cannot be recognised by the configured OCR provider.")

    def _extract_pdf_text(self, file_path: Path) -> str:
        try:
            reader = PdfReader(str(file_path))
        except Exception as exc:
            raise OCRProcessingError("CORRUPTED_FILE", "The PDF invoice could not be opened.") from exc
        if reader.is_encrypted:
            raise OCRProcessingError("ENCRYPTED_PDF", "Password-protected PDF invoices cannot be processed.")
        if len(reader.pages) > get_settings().max_invoice_pages:
            raise OCRProcessingError("TOO_MANY_PAGES", f"Invoice PDFs may contain at most {get_settings().max_invoice_pages} pages.")
        text = "\n".join((page.extract_text() or "").strip() for page in reader.pages).strip()
        if text:
            return text
        raise OCRProcessingError("OCR_TEXT_UNAVAILABLE", "This scanned PDF needs an image-PDF OCR service that is not configured on this server.")

    @staticmethod
    def _run_tesseract(file_path: Path) -> str:
        try:
            result = subprocess.run(
                ["tesseract", str(file_path), "stdout"],
                capture_output=True,
                text=True,
                check=False,
                timeout=45,
            )
        except FileNotFoundError as exc:
            raise OCRProcessingError("OCR_PROVIDER_UNAVAILABLE", "Local OCR is not installed on this server.") from exc
        except subprocess.TimeoutExpired as exc:
            raise OCRProcessingError("OCR_TIMEOUT", "Invoice recognition timed out. Please retry.") from exc
        if result.returncode != 0:
            raise OCRProcessingError("DOCUMENT_PROCESSING_FAILED", "The invoice image could not be recognised.")
        return result.stdout.strip()
