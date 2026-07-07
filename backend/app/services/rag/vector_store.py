from __future__ import annotations
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter,
    FieldCondition, MatchValue, ScoredPoint
)
from app.db.qdrant import get_qdrant
from app.core.config import settings
import uuid


COLLECTIONS = {
    settings.QDRANT_COLLECTION: 1024,   # BGE-large-en
    "incidents": 1024,
    "arch_decisions": 1024,
}


async def ensure_collections() -> None:
    client = get_qdrant()
    response = await client.get_collections()
    existing = {c.name for c in response.collections}
    for name, dim in COLLECTIONS.items():
        if name not in existing:
            await client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )


class VectorStore:
    def __init__(self):
        self.client: AsyncQdrantClient = get_qdrant()

    async def upsert(self, chunks: list, vectors: list[list[float]],
                     metadata: dict, collection: str | None = None) -> list[str]:
        col = collection or settings.QDRANT_COLLECTION
        points = []
        ids = []
        for chunk, vector in zip(chunks, vectors):
            pid = str(uuid.uuid4())
            ids.append(pid)
            points.append(PointStruct(
                id=pid,
                vector=vector,
                payload={
                    "content": chunk.text,
                    "chunk_index": chunk.index,
                    **metadata,
                    **(chunk.metadata or {}),
                },
            ))
        await self.client.upsert(collection_name=col, points=points)
        return ids

    async def upsert_single(self, id: str, vector: list[float],
                             payload: dict, collection: str) -> str:
        await self.client.upsert(
            collection_name=collection,
            points=[PointStruct(id=id, vector=vector, payload=payload)],
        )
        return id

    async def search(self, vector: list[float], collection: str,
                     top_k: int = 8, filters: dict | None = None) -> list[ScoredPoint]:
        qfilter = None
        if filters:
            conditions = [FieldCondition(key=k, match=MatchValue(value=v))
                          for k, v in filters.items()]
            qfilter = Filter(must=conditions)
        return await self.client.search(
            collection_name=collection,
            query_vector=vector,
            limit=top_k,
            with_payload=True,
            query_filter=qfilter,
        )
