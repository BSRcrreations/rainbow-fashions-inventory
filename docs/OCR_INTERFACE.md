# OCR Integration Interface

Phase 1 uses `MockOCRService`, selected by `OCR_PROVIDER=mock`.

The application code depends on `OCRService.extract_text(file_path: Path) -> str`.
Any future provider should implement the same interface in `backend/app/ai/base.py`.

Supported future provider shapes:

- Local OCR such as Tesseract
- Cloud OCR such as Google Vision or Azure Document Intelligence
- AI vision extraction
- Hybrid OCR plus LLM cleanup

The purchase workflow never updates stock during OCR. OCR output is parsed into review data, shown to the user, and stock changes only when `/purchases/{id}/confirm` succeeds.
