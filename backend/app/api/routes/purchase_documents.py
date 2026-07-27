from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.schemas.purchase import DocumentJobRead, PurchaseDocumentAccepted
from app.services.purchase_document_service import PurchaseDocumentService

router = APIRouter(prefix="/purchase-documents", tags=["Purchase Documents"])


@router.post("/upload", response_model=PurchaseDocumentAccepted, status_code=status.HTTP_202_ACCEPTED)
async def upload_purchase_document(background_tasks: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    document, job = await PurchaseDocumentService(db).upload(file, current_user)
    background_tasks.add_task(PurchaseDocumentService.process, job.id)
    payload = PurchaseDocumentAccepted(document_id=document.id, job_id=job.id, status=job.status, request_id=job.request_id)
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=payload.model_dump(mode="json"), headers={"X-Request-ID": job.request_id})


@router.get("/jobs/{job_id}", response_model=DocumentJobRead)
def get_purchase_document_job(job_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return PurchaseDocumentService(db).get_job(job_id, current_user)


@router.post("/{document_id}/retry", response_model=DocumentJobRead, status_code=status.HTTP_202_ACCEPTED)
def retry_purchase_document(document_id: UUID, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = PurchaseDocumentService(db).retry(document_id, current_user)
    background_tasks.add_task(PurchaseDocumentService.process, job.id)
    return job
