from __future__ import annotations

from pathlib import Path

from app.ai.base import OCRService


class MockOCRService(OCRService):
    def extract_text(self, file_path: Path) -> str:
        # The local provider intentionally never invents supplier or invoice data.
        # Configure a real OCR provider for extracted values; users can still create
        # a clean, editable draft when recognition is unavailable.
        return ""
