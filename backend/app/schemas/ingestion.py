from pydantic import BaseModel
import uuid
from datetime import datetime


class DocumentOut(BaseModel):
    id: uuid.UUID
    title: str
    source_type: str
    status: str
    chunk_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class IngestionJobResponse(BaseModel):
    job_id: str
    document_id: uuid.UUID
    status: str
    message: str
