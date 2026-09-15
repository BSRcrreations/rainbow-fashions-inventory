from __future__ import annotations

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from pypdf import PdfReader

from app.ai.base import OCRProcessingError, OCRService
from app.core.config import get_settings


class LocalOCRService(OCRService):
    """Read PDF text and OCR image-only pages locally without posting inventory."""

    def extract_text(self, file_path: Path) -> str:
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            return self._extract_pdf_text(file_path)
        if suffix in {".heic", ".heif"}:
            from PIL import Image, ImageOps
            from pillow_heif import register_heif_opener
            try:
                register_heif_opener()
                with TemporaryDirectory(prefix="rainbow-heic-ocr-") as directory, Image.open(file_path) as source:
                    image = ImageOps.exif_transpose(source).convert("RGB")
                    image.thumbnail((2400, 2400))
                    converted = Path(directory) / "invoice.png"
                    image.save(converted)
                    return self._run_tesseract(converted)
            except (OSError, ValueError) as exc:
                raise OCRProcessingError("CORRUPTED_FILE", "The invoice photo could not be opened. Try another photo.") from exc
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
        texts = []
        with TemporaryDirectory(prefix="rainbow-invoice-ocr-") as directory:
            for index, page in enumerate(reader.pages, start=1):
                try:
                    page_text = (page.extract_text() or "").strip()
                except Exception as exc:
                    raise OCRProcessingError("CORRUPTED_FILE", "The PDF invoice could not be read.") from exc
                if not page_text:
                    output = Path(directory) / "page"
                    try:
                        result = subprocess.run(
                            ["pdftoppm", "-f", str(index), "-l", str(index), "-singlefile",
                             "-scale-to", "2400", "-png", str(file_path), str(output)],
                            capture_output=True, check=False, timeout=45,
                        )
                    except FileNotFoundError as exc:
                        raise OCRProcessingError("OCR_PROVIDER_UNAVAILABLE", "PDF image recognition is not installed on this server.") from exc
                    except subprocess.TimeoutExpired as exc:
                        raise OCRProcessingError("OCR_TIMEOUT", "Invoice recognition timed out. Try a smaller document.") from exc
                    if result.returncode != 0 or not output.with_suffix(".png").is_file():
                        raise OCRProcessingError("DOCUMENT_PROCESSING_FAILED", "This invoice page could not be recognised. Attach the file and enter its items manually.")
                    page_text = self._run_tesseract(output.with_suffix(".png"))
                texts.append(page_text)
        text = "\n".join(texts).strip()
        if not text:
            raise OCRProcessingError("OCR_TEXT_UNAVAILABLE", "No readable invoice text was found. Attach the file and enter its items manually.")
        return text

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
