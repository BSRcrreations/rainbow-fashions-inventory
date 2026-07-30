from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import bad_request
from app.models.enums import UploadFileType
from app.models.uploaded_file import UploadedFile


class FileService:
    _PRODUCT_IMAGE_MIME_BY_EXTENSION = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }

    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    async def save_invoice_file(self, file: UploadFile, uploaded_by: Optional[UUID]) -> UploadedFile:
        extension = Path(file.filename or "invoice").suffix.lower()
        allowed_extensions = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".pdf"}
        if file.content_type not in self.settings.allowed_invoice_content_types or extension not in allowed_extensions:
            raise bad_request("Only JPG, JPEG, PNG, WEBP, HEIC, HEIF, and PDF invoice uploads are allowed", "UNSUPPORTED_FILE_TYPE")

        content = await file.read()
        if not content:
            raise bad_request("Uploaded file is empty", "EMPTY_FILE")
        if len(content) > self.settings.max_upload_size_bytes:
            raise bad_request(f"This invoice is larger than {self.settings.max_upload_size_mb} MB.", "FILE_TOO_LARGE")
        if not self._matches_invoice_signature(extension, content):
            raise bad_request("The uploaded file content does not match its invoice file type", "CORRUPTED_FILE")

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

    @classmethod
    def _product_image_mime_from_signature(cls, content: bytes) -> Optional[str]:
        """Identify supported image bytes without trusting the browser-provided MIME type."""
        if content.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if len(content) >= 12 and content.startswith(b"RIFF") and content[8:12] == b"WEBP":
            return "image/webp"
        return None

    @staticmethod
    def _product_image_mime_from_content(content: bytes) -> Optional[str]:
        """Verify the image is decodable and identify its actual encoded format."""
        try:
            with Image.open(BytesIO(content)) as image:
                image_format = image.format
                image.verify()
        except (Image.DecompressionBombError, OSError, UnidentifiedImageError, ValueError):
            return None
        return {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}.get(image_format or "")

    @classmethod
    def _validate_product_image(cls, filename: Optional[str], content_type: Optional[str], content: bytes) -> str:
        """Require extension, declared MIME type, and actual bytes to describe the same format."""
        extension = Path(filename or "product").suffix.lower()
        expected_mime = cls._PRODUCT_IMAGE_MIME_BY_EXTENSION.get(extension)
        if not expected_mime:
            raise bad_request("Product image filename must end with jpg, jpeg, png, or webp", "UNSUPPORTED_FILE_TYPE")
        if content_type not in get_settings().allowed_product_image_content_types:
            raise bad_request("Only JPG, JPEG, PNG, and WEBP product images are allowed", "UNSUPPORTED_FILE_TYPE")

        signature_mime = cls._product_image_mime_from_signature(content)
        detected_mime = cls._product_image_mime_from_content(content)
        if not signature_mime or not detected_mime:
            raise bad_request("The uploaded image is not a valid JPG, PNG, or WEBP file", "CORRUPTED_FILE")
        if signature_mime != detected_mime or content_type != detected_mime or expected_mime != detected_mime:
            raise bad_request("The uploaded image MIME type, filename, and file content must match", "CORRUPTED_FILE")
        return extension

    async def save_product_image(self, file: UploadFile, uploaded_by: Optional[UUID]) -> UploadedFile:
        content = await file.read()
        if not content:
            raise bad_request("Uploaded image is empty", "EMPTY_FILE")
        if len(content) > self.settings.max_product_image_size_bytes:
            raise bad_request(f"Product image exceeds {self.settings.max_product_image_size_mb} MB", "FILE_TOO_LARGE")

        extension = self._validate_product_image(file.filename, file.content_type, content)

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
