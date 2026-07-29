# OCR Integration Interface

The default local provider is selected with `OCR_PROVIDER=local`.

`LocalOCRService` extracts text-native PDFs with `pypdf` and sends JPG, PNG,
and WebP images to the locally installed Tesseract executable. It never
manufactures supplier or product values. Image-only PDFs, HEIC/HEIF files,
encrypted PDFs, and PDFs over the configured page limit return a specific safe
job failure code for review or retry. `OCR_PROVIDER=mock` remains available for
deterministic development tests and returns an empty editable draft.

The application code depends on `OCRService.extract_text(file_path: Path) -> str`.
Any future provider should implement the same interface in `backend/app/ai/base.py`.

Supported future provider shapes:

- Local OCR such as Tesseract
- Cloud OCR such as Google Vision or Azure Document Intelligence
- AI vision extraction
- Hybrid OCR plus LLM cleanup

The purchase workflow never updates stock during OCR. OCR output is parsed into review data, shown to the user, and stock changes only when `/purchases/{id}/confirm` succeeds.
