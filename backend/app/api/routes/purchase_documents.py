from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.models.uploaded_file import UploadedFile
from app.schemas.purchase import DocumentJobRead, PurchaseDocumentAccepted, PurchaseDocumentRead
from app.services.purchase_document_service import PurchaseDocumentService

router = APIRouter(prefix="/purchase-documents", tags=["Purchase Documents"])


@router.post("/upload", response_model=PurchaseDocumentAccepted, status_code=status.HTTP_202_ACCEPTED)
async def upload_purchase_document(background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    document, job, created = await PurchaseDocumentService(db).upload(file, current_user)
    if created:
        background_tasks.add_task(PurchaseDocumentService.process, job.id)
    payload = PurchaseDocumentAccepted(document_id=document.id, job_id=job.id, status=job.status, request_id=job.request_id, duplicate=not created)
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=payload.model_dump(mode="json"), headers={"X-Request-ID": job.request_id})


@router.get("/jobs/{job_id}", response_model=DocumentJobRead)
def get_purchase_document_job(job_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return PurchaseDocumentService(db).get_job(job_id, current_user)


@router.get("/{document_id}", response_model=PurchaseDocumentRead)
def get_purchase_document(document_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> PurchaseDocumentRead:
    document = PurchaseDocumentService(db).get_document(document_id, current_user)
    uploaded = db.get(UploadedFile, document.uploaded_file_id)
    if not uploaded:
        from app.core.exceptions import not_found

        raise not_found("Uploaded invoice file")
    return PurchaseDocumentRead(
        id=document.id,
        original_filename=uploaded.original_filename,
        content_type=uploaded.content_type,
        file_size_bytes=uploaded.file_size_bytes,
        sha256=document.sha256,
    )


@router.get("/{document_id}/preview")
def preview_purchase_document(document_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> FileResponse:
    document = PurchaseDocumentService(db).get_document(document_id, current_user)
    uploaded = db.get(UploadedFile, document.uploaded_file_id)
    if not uploaded:
        from app.core.exceptions import not_found

        raise not_found("Uploaded invoice file")
    return FileResponse(uploaded.storage_path, media_type=uploaded.content_type, filename=uploaded.original_filename, content_disposition_type="inline")


@router.post("/{document_id}/retry", response_model=DocumentJobRead, status_code=status.HTTP_202_ACCEPTED)
def retry_purchase_document(document_id: UUID, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job, created = PurchaseDocumentService(db).retry(document_id, current_user)
    if created:
        background_tasks.add_task(PurchaseDocumentService.process, job.id)
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=DocumentJobRead.model_validate(job).model_dump(mode="json"), headers={"X-Request-ID": job.request_id})
