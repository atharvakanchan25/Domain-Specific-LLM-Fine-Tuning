"""
Module 1: Data Ingestion Engine
Orchestrates parsing → chunking → embedding → storage pipeline.
"""
from __future__ import annotations
import subprocess
from pathlib import Path
from typing import Protocol
from app.core.config import settings
from app.core.logging import logger
from app.services.ingestion.parsers.pdf import PDFParser
from app.services.ingestion.parsers.markdown import MarkdownParser
from app.services.ingestion.parsers.code import CodeParser, TextParser


class BaseParser(Protocol):
    async def parse(self, path: Path) -> str:
        ...


_PARSERS: dict[str, object] = {
    "pdf":      PDFParser(),
    "markdown": MarkdownParser(),
    "code":     CodeParser(),
    "text":     TextParser(),
    "git":      TextParser(),
    "log":      TextParser(),
    "api_spec": TextParser(),
}


class IngestionEngine:
    def __init__(self, chunker, embedder, vector_store, graph_builder, db_session):
        self.chunker = chunker
        self.embedder = embedder
        self.vector_store = vector_store
        self.graph_builder = graph_builder
        self.db = db_session

    async def ingest_document(self, file_path: Path, source_type: str,
                               document_id: str | None = None) -> dict:
        """Route a document to the correct parser then run the pipeline."""
        logger.info("ingest_document", path=str(file_path), type=source_type)
        parser = _PARSERS.get(source_type, _PARSERS["text"])
        content = await parser.parse(file_path)
        metadata = {
            "source_path": str(file_path),
            "source_type": source_type,
            "document_id": document_id or "",
        }
        ids = await self._run_pipeline(content, metadata)
        await self._extract_and_store_entities(content)
        logger.info("ingest_document_done", chunks=len(ids))
        return {"chunk_ids": ids, "chunk_count": len(ids)}

    async def ingest_git_repo(self, repo_url: str, repo_name: str,
                               branch: str = "main") -> dict:
        """Clone repo, walk code files and commit history, ingest all."""
        logger.info("ingest_git_repo", repo=repo_name)
        repo_path = Path(settings.GIT_REPOS_PATH) / repo_name
        repo_path.parent.mkdir(parents=True, exist_ok=True)

        if repo_path.exists():
            subprocess.run(["git", "-C", str(repo_path), "pull"], check=False)
        else:
            subprocess.run(
                ["git", "clone", "--depth", "50", "--branch", branch, repo_url, str(repo_path)],
                check=True,
            )

        total_ids: list[str] = []
        code_extensions = {".py", ".js", ".ts", ".java", ".go", ".rb",
                           ".md", ".yaml", ".yml", ".json", ".txt"}
        for file in repo_path.rglob("*"):
            if file.is_file() and file.suffix in code_extensions:
                try:
                    content = file.read_text(encoding="utf-8", errors="ignore")
                    if not content.strip():
                        continue
                    metadata = {
                        "source_path": str(file.relative_to(repo_path)),
                        "source_type": "git",
                        "repo_name": repo_name,
                    }
                    ids = await self._run_pipeline(content, metadata)
                    total_ids.extend(ids)
                except Exception as exc:
                    logger.warning("git_file_skip", file=str(file), error=str(exc))

        # Ingest commit messages
        try:
            log = subprocess.check_output(
                ["git", "-C", str(repo_path), "log", "--oneline", "-200"],
                text=True, errors="ignore",
            )
            if log.strip():
                ids = await self._run_pipeline(
                    log,
                    {"source_path": "git_log", "source_type": "commit", "repo_name": repo_name},
                )
                total_ids.extend(ids)
        except Exception as exc:
            logger.warning("git_log_skip", error=str(exc))

        logger.info("ingest_git_repo_done", repo=repo_name, chunks=len(total_ids))
        return {"chunk_ids": total_ids, "chunk_count": len(total_ids)}

    async def ingest_jira_tickets(self, tickets: list[dict]) -> dict:
        """Ingest Jira/incident data for bug intelligence engine."""
        logger.info("ingest_jira_tickets", count=len(tickets))
        ids: list[str] = []
        for ticket in tickets:
            text = (
                f"{ticket.get('title', '')}\n"
                f"{ticket.get('description', '')}\n"
                f"Root cause: {ticket.get('root_cause', '')}\n"
                f"Resolution: {ticket.get('resolution', '')}"
            )
            metadata = {
                "source_path": ticket.get("id", ""),
                "source_type": "incident",
                "title": ticket.get("title", ""),
                "root_cause": ticket.get("root_cause", ""),
                "resolution": ticket.get("resolution", ""),
                "affected_service": ticket.get("affected_service", ""),
            }
            chunk_ids = await self._run_pipeline(text, metadata)
            # Also upsert into the dedicated incidents collection
            vector = await self.embedder.embed(text)
            await self.vector_store.upsert_single(
                id=ticket.get("id", chunk_ids[0] if chunk_ids else ""),
                vector=vector,
                payload=metadata,
                collection="incidents",
            )
            ids.extend(chunk_ids)
        return {"chunk_count": len(ids)}

    async def _run_pipeline(self, content: str, metadata: dict) -> list[str]:
        """Shared: chunk → embed → store in Qdrant."""
        chunks = self.chunker.chunk(content, metadata)
        if not chunks:
            return []
        vectors = await self.embedder.embed_batch([c.text for c in chunks])
        ids = await self.vector_store.upsert(chunks, vectors, metadata)
        return ids

    async def _extract_and_store_entities(self, content: str) -> None:
        """Run entity extraction and write results to Neo4j."""
        if self.graph_builder is None:
            return
        try:
            from app.services.ingestion.entity_extractor import extract
            entities, relations = extract(content)
            entity_dicts = [{"label": e.label, "properties": e.properties} for e in entities]
            relation_dicts = [
                {
                    "from_name": r.from_name, "from_label": r.from_label,
                    "to_name": r.to_name, "to_label": r.to_label,
                    "rel_type": r.rel_type, "props": r.props,
                }
                for r in relations
            ]
            await self.graph_builder.build_from_document(entity_dicts, relation_dicts)
        except Exception as exc:
            logger.warning("entity_extraction_failed", error=str(exc))
