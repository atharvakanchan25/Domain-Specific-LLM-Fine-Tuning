"""
Hybrid retrieval: Qdrant vector search + Neo4j graph context.
"""
from __future__ import annotations
from app.db.qdrant import get_qdrant
from app.db.neo4j import get_driver
from app.core.config import settings
from app.core.logging import logger


class RAGQueryService:

    def __init__(self, embedder):
        self.embedder = embedder

    async def retrieve(self, query: str, top_k: int = 8, filters: dict | None = None) -> list[dict]:
        vector = await self.embedder.embed(query)
        qdrant = get_qdrant()
        results = await qdrant.search(
            collection_name=settings.QDRANT_COLLECTION,
            query_vector=vector,
            limit=top_k,
            with_payload=True,
        )
        chunks = [{"content": r.payload.get("content", ""), "score": r.score,
                   "metadata": r.payload, "id": str(r.id)} for r in results]
        logger.info("rag_retrieve", query=query[:60], hits=len(chunks))
        return chunks

    async def retrieve_with_graph(self, query: str, entity_name: str | None = None) -> dict:
        """Enrich vector results with KG relationships."""
        chunks = await self.retrieve(query)
        graph_context = []
        if entity_name:
            driver = get_driver()
            async with driver.session() as s:
                result = await s.run(
                    """
                    MATCH (n {name: $name})-[r]-(related)
                    RETURN type(r) AS rel, labels(related)[0] AS type,
                           related.name AS name LIMIT 20
                    """,
                    name=entity_name,
                )
                graph_context = [dict(rec) async for rec in result]
        return {"chunks": chunks, "graph_context": graph_context}
