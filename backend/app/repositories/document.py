from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.domain import Document, DocumentChunk, SourceType
import uuid


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, title: str, source_type: str, source_path: str | None = None,
                     content_hash: str | None = None, metadata: dict | None = None) -> Document:
        doc = Document(title=title, source_type=SourceType(source_type),
                       source_path=source_path, content_hash=content_hash,
                       metadata_=metadata)
        self.db.add(doc)
        await self.db.commit()
        await self.db.refresh(doc)
        return doc

    async def get_by_id(self, doc_id: uuid.UUID) -> Document | None:
        result = await self.db.execute(select(Document).where(Document.id == doc_id))
        return result.scalar_one_or_none()

    async def get_by_hash(self, content_hash: str) -> Document | None:
        result = await self.db.execute(select(Document).where(Document.content_hash == content_hash))
        return result.scalar_one_or_none()

    async def update_status(self, doc_id: uuid.UUID, status: str, chunk_count: int = 0) -> None:
        await self.db.execute(
            update(Document).where(Document.id == doc_id)
            .values(status=status, chunk_count=chunk_count)
        )
        await self.db.commit()

    async def add_chunks(self, doc_id: uuid.UUID, chunks: list[dict]) -> None:
        for c in chunks:
            self.db.add(DocumentChunk(
                document_id=doc_id,
                chunk_index=c["index"],
                content=c["text"],
                token_count=c["token_count"],
                qdrant_id=c.get("qdrant_id"),
                metadata_=c.get("metadata"),
            ))
        await self.db.commit()
