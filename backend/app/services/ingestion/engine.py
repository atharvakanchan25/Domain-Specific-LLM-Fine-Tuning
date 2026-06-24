"""
Module 1: Data Ingestion Engine
Orchestrates parsing → chunking → embedding → storage pipeline.
"""
from __future__ import annotations
from pathlib import Path
from typing import Protocol
from app.core.logging import logger


class BaseParser(Protocol):
    async def parse(self, path: Path) -> str:
        ...


class IngestionEngine:
    """
    Entry-point for all ingestion jobs.
    Each source type delegates to a specialised parser then goes through
    the shared chunk → embed → store pipeline.
    """

    def __init__(self, chunker, embedder, vector_store, graph_builder, db_session):
        self.chunker = chunker
        self.embedder = embedder
        self.vector_store = vector_store
        self.graph_builder = graph_builder
        self.db = db_session

    async def ingest_git_repo(self, repo_path: str, repo_name: str) -> dict:
        """Parse commits, code files, PR descriptions from a git repo."""
        # TODO: implement in Module 1 build-out
        logger.info("ingest_git_repo", repo=repo_name)
        raise NotImplementedError

    async def ingest_document(self, file_path: Path, source_type: str) -> dict:
        """Route a document to the correct parser then run the pipeline."""
        # TODO: implement in Module 1 build-out
        logger.info("ingest_document", path=str(file_path), type=source_type)
        raise NotImplementedError

    async def ingest_jira_tickets(self, tickets: list[dict]) -> dict:
        """Ingest Jira/incident data for bug intelligence engine."""
        logger.info("ingest_jira_tickets", count=len(tickets))
        raise NotImplementedError

    async def _run_pipeline(self, content: str, metadata: dict) -> list[str]:
        """Shared: chunk → embed → store in Qdrant + PostgreSQL."""
        chunks = self.chunker.chunk(content)
        vectors = await self.embedder.embed_batch([c.text for c in chunks])
        ids = await self.vector_store.upsert(chunks, vectors, metadata)
        return ids
