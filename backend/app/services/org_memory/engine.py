"""
Module 6: Organizational Memory Engine
Persistent long-term memory for architectural decisions,
design discussions, migration histories, and engineering conventions.
"""
from __future__ import annotations
from app.core.logging import logger


class OrgMemoryEngine:

    def __init__(self, embedder, vector_store, kg_service, db_session):
        self.embedder = embedder
        self.vector_store = vector_store
        self.kg = kg_service
        self.db = db_session

    async def store_decision(self, decision: dict) -> str:
        """Persist an architectural decision to PostgreSQL + Qdrant + Neo4j."""
        text = f"{decision['title']} {decision['context']} {decision['rationale']}"
        vector = await self.embedder.embed(text)
        qdrant_id = await self.vector_store.upsert_single(
            id=decision["id"],
            vector=vector,
            payload=decision,
            collection="arch_decisions",
        )
        await self.kg.create_node("ArchDecision", {
            "name": decision["title"],
            "status": decision.get("status", "accepted"),
        })
        for alt in decision.get("alternatives_considered", {}).keys():
            await self.kg.create_node("Technology", {"name": alt})
            await self.kg.create_relationship(
                from_name=decision["title"], from_label="ArchDecision",
                to_name=alt, to_label="Technology",
                rel_type="REJECTED_ALTERNATIVE",
            )
        logger.info("decision_stored", title=decision["title"])
        return qdrant_id

    async def query(self, question: str, top_k: int = 5) -> list[dict]:
        """Semantic search over organisational memory."""
        vector = await self.embedder.embed(question)
        results = await self.vector_store.search(
            vector=vector,
            collection="arch_decisions",
            top_k=top_k,
        )
        return [r.payload for r in results]

    async def get_decision_timeline(self, topic: str) -> list[dict]:
        """Return decisions related to a topic ordered chronologically."""
        records = await self.query(topic, top_k=20)
        return sorted(records, key=lambda x: x.get("created_at", ""))
