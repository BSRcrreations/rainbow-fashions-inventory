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
        extension = Path(file.filename or "invoice").suffix.lower()
        allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".pdf"}
        if file.content_type not in self.settings.allowed_invoice_content_types or extension not in allowed_extensions:
            raise bad_request("Only JPG, JPEG, PNG, WEBP, HEIC, HEIF, and PDF invoice uploads are allowed")

        content = await file.read()
        if not content:
            raise bad_request("Uploaded file is empty")
        if len(content) > self.settings.max_upload_size_bytes:
            raise bad_request(f"Uploaded file exceeds {self.settings.max_upload_size_mb} MB")
        if not self._matches_invoice_signature(extension, content):
            raise bad_request("The uploaded file content does not match its invoice file type")

        upload_dir = self.settings.invoice_upload_dir
        upload_dir.mkdir(parents=True, exist_ok=True)
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

    @staticmethod
    def _matches_invoice_signature(extension: str, content: bytes) -> bool:
        if extension == ".pdf":
            return content.startswith(b"%PDF-")
        if extension in {".jpg", ".jpeg"}:
            return content.startswith(b"\xff\xd8\xff")
        if extension == ".png":
            return content.startswith(b"\x89PNG\r\n\x1a\n")
        if extension == ".webp":
            return len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP"
        if extension in {".heic", ".heif"}:
            return len(content) >= 12 and content[4:8] == b"ftyp" and content[8:12] in {b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"}
        return False

    async def save_product_image(self, file: UploadFile, uploaded_by: Optional[UUID]) -> UploadedFile:
        if file.content_type not in self.settings.allowed_product_image_content_types:
            raise bad_request("Only JPG, PNG, and WEBP product images are allowed")

        content = await file.read()
        if not content:
            raise bad_request("Uploaded image is empty")
        if len(content) > self.settings.max_product_image_size_bytes:
            raise bad_request(f"Product image exceeds {self.settings.max_product_image_size_mb} MB")

        extension = Path(file.filename or "product").suffix.lower()
        allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
        if extension not in allowed_extensions:
            raise bad_request("Product image filename must end with jpg, jpeg, png, or webp")

        upload_dir = self.settings.product_upload_dir
        upload_dir.mkdir(parents=True, exist_ok=True)
        stored_filename = f"{uuid4()}{extension}"
        storage_path = upload_dir / stored_filename
        storage_path.write_bytes(content)

        uploaded_file = UploadedFile(
            file_type=UploadFileType.PRODUCT_IMAGE,
            original_filename=Path(file.filename or stored_filename).name,
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

    def delete_product_image_path(self, image_url: Optional[str]) -> None:
        if not image_url:
            return
        filename = Path(image_url).name
        if not filename:
            return
        upload_dir = self.settings.product_upload_dir.resolve()
        target = (upload_dir / filename).resolve()
        if upload_dir not in target.parents and target != upload_dir:
            raise bad_request("Invalid product image path")
        if target.exists() and target.is_file():
            target.unlink()
