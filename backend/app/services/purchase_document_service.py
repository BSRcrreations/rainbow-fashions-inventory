from __future__ import annotations

import logging
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import UploadFile
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.ai.factory import get_ocr_service
from app.ai.invoice_parser import InvoiceParser
from app.core.exceptions import bad_request, not_found
from app.database.session import SessionLocal
from app.models.enums import DocumentJobStatus
from app.models.purchase_document import DocumentProcessingJob, PurchaseDocument
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.services.file_service import FileService
from app.services.purchase_service import PurchaseService

logger = logging.getLogger(__name__)


class PurchaseDocumentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    async def upload(self, file: UploadFile, current_user: User) -> tuple[PurchaseDocument, DocumentProcessingJob]:
        store_id = self._store_id(current_user)
        uploaded = await FileService(self.db).save_invoice_file(file, current_user.id)
        document = PurchaseDocument(store_id=store_id, uploaded_file_id=uploaded.id, sha256=sha256(Path(uploaded.storage_path).read_bytes()).hexdigest(), created_by=current_user.id)
        self.db.add(document)
        self.db.flush()
        job = DocumentProcessingJob(document_id=document.id, store_id=store_id, status=DocumentJobStatus.QUEUED, progress=5, message="Invoice saved and queued for recognition", request_id=str(uuid4()), provider="mock")
        self.db.add(job)
        self.db.commit()
        logger.info("purchase_document_uploaded request_id=%s store_id=%s user_id=%s document_id=%s job_id=%s filename=%s mime=%s size=%s", job.request_id, store_id, current_user.id, document.id, job.id, file.filename, file.content_type, uploaded.file_size_bytes)
        return document, job

    def get_job(self, job_id: UUID, current_user: User) -> DocumentProcessingJob:
        job = self.db.query(DocumentProcessingJob).filter(DocumentProcessingJob.id == job_id, DocumentProcessingJob.store_id == self._store_id(current_user)).first()
        if not job:
            raise not_found("Document processing job")
        return job

    def get_document(self, document_id: UUID, current_user: User) -> PurchaseDocument:
        document = self.db.query(PurchaseDocument).filter(PurchaseDocument.id == document_id, PurchaseDocument.store_id == self._store_id(current_user)).first()
        if not document:
            raise not_found("Purchase document")
        return document

    def retry(self, document_id: UUID, current_user: User) -> DocumentProcessingJob:
        document = self.get_document(document_id, current_user)
        job = DocumentProcessingJob(document_id=document.id, store_id=document.store_id, status=DocumentJobStatus.QUEUED, progress=5, message="Recognition retry queued", request_id=str(uuid4()), provider="mock")
        self.db.add(job)
        self.db.commit()
        logger.info("purchase_document_retry_queued request_id=%s store_id=%s user_id=%s document_id=%s job_id=%s", job.request_id, document.store_id, current_user.id, document.id, job.id)
        return job

    @staticmethod
    def process(job_id: UUID) -> None:
        db = SessionLocal()
        try:
            job = db.get(DocumentProcessingJob, job_id)
            if not job:
                return
            document = db.get(PurchaseDocument, job.document_id)
            uploaded = db.get(UploadedFile, document.uploaded_file_id) if document else None
            if not document or not uploaded:
                raise RuntimeError("Stored document is unavailable")
            job.status, job.progress, job.message, job.started_at = DocumentJobStatus.PREPROCESSING, 15, "Preparing document", datetime.now(timezone.utc)
            db.commit()
            logger.info("purchase_document_processing request_id=%s job_id=%s stage=preprocessing", job.request_id, job.id)
            job.status, job.progress, job.message = DocumentJobStatus.OCR_RUNNING, 40, "Reading invoice text"
            db.commit()
            raw_text = get_ocr_service().extract_text(Path(uploaded.storage_path))
            job.status, job.progress, job.message = DocumentJobStatus.AI_EXTRACTION, 60, "Extracting structured invoice data"
            db.commit()
            invoice = InvoiceParser().parse(raw_text)
            review_items = PurchaseService(db)._build_review_items(invoice)
            job.status, job.progress, job.message = DocumentJobStatus.REVIEW_REQUIRED, 100, "Invoice draft is ready for review"
            job.result = jsonable_encoder({"extracted_invoice": invoice, "review_items": review_items, "warnings": []})
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            logger.info("purchase_document_review_ready request_id=%s job_id=%s document_id=%s", job.request_id, job.id, document.id)
        except Exception as exc:
            db.rollback()
            job = db.get(DocumentProcessingJob, job_id)
            if job:
                job.status, job.progress, job.message = DocumentJobStatus.FAILED, 100, "Invoice recognition could not be completed"
                job.error_code, job.error_message, job.completed_at = "DOCUMENT_PROCESSING_FAILED", "We saved the invoice, but could not complete recognition. Retry processing from the review screen.", datetime.now(timezone.utc)
                db.commit()
            logger.exception("purchase_document_processing_failed job_id=%s exception_type=%s", job_id, type(exc).__name__)
        finally:
            db.close()

    def _store_id(self, current_user: User) -> UUID:
        if current_user.store_id is None:
            raise bad_request("Current user is not assigned to a store")
        return current_user.store_id
