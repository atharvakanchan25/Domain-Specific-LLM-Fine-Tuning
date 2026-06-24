from app.workers.celery_app import celery_app
from app.core.logging import logger


@celery_app.task(bind=True, name="tasks.ingest_document")
def task_ingest_document(self, file_path: str, source_type: str, document_id: str):
    logger.info("task_ingest_document", file=file_path, doc_id=document_id)
    # TODO: run asyncio.run(ingestion_engine.ingest_document(...))
    raise NotImplementedError


@celery_app.task(bind=True, name="tasks.ingest_git_repo")
def task_ingest_git(self, repo_url: str, branch: str, repo_name: str):
    logger.info("task_ingest_git", repo=repo_url)
    raise NotImplementedError


@celery_app.task(bind=True, name="tasks.build_knowledge_graph")
def task_build_kg(self, document_id: str):
    logger.info("task_build_kg", doc_id=document_id)
    raise NotImplementedError


@celery_app.task(bind=True, name="tasks.index_incident")
def task_index_incident(self, incident: dict):
    logger.info("task_index_incident", id=incident.get("id"))
    raise NotImplementedError
