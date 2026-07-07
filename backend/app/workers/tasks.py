import asyncio
from pathlib import Path
from app.workers.celery_app import celery_app
from app.core.logging import logger


def _make_engine():
    from app.services.rag.chunker import Chunker
    from app.services.rag.embedder import Embedder
    from app.services.rag.vector_store import VectorStore
    from app.services.knowledge_graph.service import KnowledgeGraphService
    from app.services.ingestion.engine import IngestionEngine
    return IngestionEngine(
        chunker=Chunker(),
        embedder=Embedder(),
        vector_store=VectorStore(),
        graph_builder=KnowledgeGraphService(),
        db_session=None,
    )


@celery_app.task(bind=True, name="tasks.ingest_document")
def task_ingest_document(self, file_path: str, source_type: str, document_id: str):
    logger.info("task_ingest_document", file=file_path, doc_id=document_id)
    engine = _make_engine()
    result = asyncio.run(engine.ingest_document(Path(file_path), source_type, document_id))
    return result


@celery_app.task(bind=True, name="tasks.ingest_git_repo")
def task_ingest_git(self, repo_url: str, branch: str, repo_name: str):
    logger.info("task_ingest_git", repo=repo_url)
    engine = _make_engine()
    result = asyncio.run(engine.ingest_git_repo(repo_url, repo_name, branch))
    return result


@celery_app.task(bind=True, name="tasks.build_knowledge_graph")
def task_build_kg(self, document_id: str):
    logger.info("task_build_kg", doc_id=document_id)
    # KG is built inline during ingest_document; this task is a no-op hook
    return {"status": "kg_built_inline", "document_id": document_id}


@celery_app.task(bind=True, name="tasks.index_incident")
def task_index_incident(self, incident: dict):
    logger.info("task_index_incident", id=incident.get("id"))
    engine = _make_engine()
    result = asyncio.run(engine.ingest_jira_tickets([incident]))
    return result
