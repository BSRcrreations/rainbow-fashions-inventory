from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class OCRService(ABC):
    @abstractmethod
    def extract_text(self, file_path: Path) -> str:
        raise NotImplementedError


class OCRProcessingError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
