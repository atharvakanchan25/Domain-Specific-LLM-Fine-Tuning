from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1 import auth, ingestion, query, graph
from app.db.neo4j import close_driver
from app.services.rag.embedder import Embedder
from app.services.rag.vector_store import VectorStore
from app.services.rag.query import RAGQueryService
from app.services.knowledge_graph.service import KnowledgeGraphService
from app.services.bug_intelligence.engine import BugIntelligenceEngine
from app.services.org_memory.engine import OrgMemoryEngine
from app.services.agents.specialized import (
    CodeAnalysisAgent, ArchitectureAgent, BugDiagnosisAgent, OrgMemoryAgent
)
from app.services.agents.orchestrator import set_dependencies

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    embedder     = Embedder()
    vector_store = VectorStore()
    rag          = RAGQueryService(embedder)
    kg           = KnowledgeGraphService()
    bug_engine   = BugIntelligenceEngine(embedder, vector_store, None)
    org_memory   = OrgMemoryEngine(embedder, vector_store, kg, None)

    set_dependencies({
        "code_analysis_agent": CodeAnalysisAgent(rag),
        "architecture_agent":  ArchitectureAgent(rag, kg),
        "bug_diagnosis_agent": BugDiagnosisAgent(bug_engine),
        "org_memory_agent":    OrgMemoryAgent(org_memory),
    })
    yield
    await close_driver()


app = FastAPI(
    title="Enterprise Knowledge-Aware LLM",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.APP_ENV != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

app.include_router(auth.router,      prefix="/api/v1")
app.include_router(ingestion.router, prefix="/api/v1")
app.include_router(query.router,     prefix="/api/v1")
app.include_router(graph.router,     prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
