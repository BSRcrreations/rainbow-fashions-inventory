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


def test_local_ocr_processes_mixed_text_and_scanned_pdf_pages(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import app.ai.local_ocr as module
    monkeypatch.setattr(module, "PdfReader", lambda _: SimpleNamespace(is_encrypted=False, pages=[SimpleNamespace(extract_text=lambda: "Supplier: Test"), SimpleNamespace(extract_text=lambda: "")]))
    rendered = []
    def run(command, **kwargs):
        rendered.append(command)
        Path(command[-1]).with_suffix('.png').write_bytes(b'test-render')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(module.subprocess, 'run', run)
    monkeypatch.setattr(LocalOCRService, '_run_tesseract', staticmethod(lambda path: 'Invoice: 123'))
    assert LocalOCRService().extract_text(tmp_path/'mixed.pdf') == 'Supplier: Test\nInvoice: 123'
    assert rendered[0][1:5] == ['-f', '2', '-l', '2']
    assert not Path(rendered[0][-1]).parent.exists()


def test_scanned_pdf_timeout_is_safe_and_temporary_files_are_removed(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import app.ai.local_ocr as module
    monkeypatch.setattr(module, 'PdfReader', lambda _: SimpleNamespace(is_encrypted=False, pages=[SimpleNamespace(extract_text=lambda: '')]))
    paths=[]
    def timeout(command, **kwargs):
        paths.append(Path(command[-1]).parent)
        raise module.subprocess.TimeoutExpired(command, 45)
    monkeypatch.setattr(module.subprocess, 'run', timeout)
    with pytest.raises(OCRProcessingError) as failure: LocalOCRService().extract_text(tmp_path/'scan.pdf')
    assert failure.value.code == 'OCR_TIMEOUT'
    assert not paths[0].exists()
