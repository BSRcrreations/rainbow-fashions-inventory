from __future__ import annotations

from app.ai.base import OCRService
from app.ai.mock_ocr import MockOCRService
from app.core.config import get_settings


def get_ocr_service() -> OCRService:
    settings = get_settings()
    if settings.ocr_provider == "mock":
        return MockOCRService()
    return MockOCRService()
