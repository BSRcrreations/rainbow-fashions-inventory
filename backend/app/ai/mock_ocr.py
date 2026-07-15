from __future__ import annotations

from pathlib import Path

from app.ai.base import OCRService


class MockOCRService(OCRService):
    def extract_text(self, file_path: Path) -> str:
        return """
Supplier: ARK Distributors
Invoice Number: ARK-INV-1001
Date: 2026-07-14
Items:
Prisma | Leggins | Cotton Leggins | M | Black | 6 | 180.00 | 349.00 | 1080.00
Flybirds | Kurty | Printed Rayon Kurty | XL | Maroon | 4 | 420.00 | 899.00 | 1680.00
Jockey | Bra | Everyday Comfort Bra | 34B | Skin | 3 | 320.00 | 499.00 | 960.00
Total: 3720.00
""".strip()
