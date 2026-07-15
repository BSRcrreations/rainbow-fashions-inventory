from __future__ import annotations

from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import bad_request
from app.models.enums import UploadFileType
from app.models.uploaded_file import UploadedFile


class FileService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    async def save_invoice_file(self, file: UploadFile, uploaded_by: Optional[UUID]) -> UploadedFile:
        if file.content_type not in self.settings.allowed_invoice_content_types:
            raise bad_request("Only JPG, PNG, and PDF invoice uploads are allowed")

        content = await file.read()
        if not content:
            raise bad_request("Uploaded file is empty")
        if len(content) > self.settings.max_upload_size_bytes:
            raise bad_request(f"Uploaded file exceeds {self.settings.max_upload_size_mb} MB")

        upload_dir = self.settings.invoice_upload_dir
        upload_dir.mkdir(parents=True, exist_ok=True)
        extension = Path(file.filename or "invoice").suffix.lower()
        stored_filename = f"{uuid4()}{extension}"
        storage_path = upload_dir / stored_filename
        storage_path.write_bytes(content)

        file_type = UploadFileType.INVOICE_PDF if file.content_type == "application/pdf" else UploadFileType.INVOICE_IMAGE
        uploaded_file = UploadedFile(
            file_type=file_type,
            original_filename=file.filename or stored_filename,
            stored_filename=stored_filename,
            content_type=file.content_type or "application/octet-stream",
            file_size_bytes=len(content),
            storage_path=str(storage_path),
            uploaded_by=uploaded_by,
        )
        self.db.add(uploaded_file)
        self.db.flush()
        self.db.refresh(uploaded_file)
        return uploaded_file
