import hashlib
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.db.session import get_db
from app.repositories.document import DocumentRepository
from app.workers.tasks import task_ingest_document, task_ingest_git
from app.schemas.ingestion import IngestionJobResponse
import uuid

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/document", response_model=IngestionJobResponse)
async def ingest_document(
    file: UploadFile = File(...),
    source_type: str = Form(...),
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    content = await file.read()
    content_hash = hashlib.sha256(content).hexdigest()

    repo = DocumentRepository(db)
    existing = await repo.get_by_hash(content_hash)
    if existing:
        raise HTTPException(status_code=409, detail="Document already ingested")

    doc = await repo.create(
        title=file.filename or "untitled",
        source_type=source_type,
        content_hash=content_hash,
    )
    dest = UPLOAD_DIR / f"{doc.id}_{file.filename}"
    dest.write_bytes(content)

    job = task_ingest_document.delay(str(dest), source_type, str(doc.id))
    return IngestionJobResponse(job_id=job.id, document_id=doc.id,
                                status="queued", message="Ingestion started")


@router.post("/git", response_model=IngestionJobResponse)
async def ingest_git(
    repo_url: str = Form(...),
    branch: str = Form("main"),
    user=Depends(get_current_user),
):
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    job = task_ingest_git.delay(repo_url, branch, repo_name)
    return IngestionJobResponse(
        job_id=job.id,
        document_id=uuid.uuid4(),
        status="queued",
        message=f"Git ingestion queued for {repo_name}",
    )


@router.get("/status/{job_id}")
async def ingestion_status(job_id: str, user=Depends(get_current_user)):
    from app.workers.celery_app import celery_app
    result = celery_app.AsyncResult(job_id)
    return {"job_id": job_id, "status": result.status, "result": result.result}
