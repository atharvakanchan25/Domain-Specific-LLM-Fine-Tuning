from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.db.session import get_db
from app.schemas.query import QueryRequest, QueryResponse, DiagnosisRequest, DiagnosisResponse
from app.services.agents.orchestrator import agent_graph, AgentState
from app.services.bug_intelligence.engine import BugIntelligenceEngine
from app.services.rag.embedder import Embedder
from app.services.rag.vector_store import VectorStore
import uuid

router = APIRouter(prefix="/query", tags=["query"])


@router.post("/", response_model=QueryResponse)
async def query(body: QueryRequest, user=Depends(get_current_user)):
    conv_id = body.conversation_id or str(uuid.uuid4())
    initial: AgentState = {
        "query": body.question,
        "entity_hint": body.entity_hint,
        "plan": "",
        "agent_outputs": [],
        "citations": [],
        "graph_context": [],
        "answer": "",
        "confidence": 0.0,
    }
    result = await agent_graph.ainvoke(initial)
    return QueryResponse(
        answer=result["answer"],
        conversation_id=conv_id,
        plan=result["plan"],
        agent_outputs=result["agent_outputs"],
        citations=result["citations"],
        graph_context=result["graph_context"],
        confidence=result["confidence"],
    )


@router.post("/diagnose", response_model=DiagnosisResponse)
async def diagnose_bug(body: DiagnosisRequest, user=Depends(get_current_user)):
    engine = BugIntelligenceEngine(Embedder(), VectorStore(), None)
    result = await engine.diagnose(body.error_description, body.service)
    return DiagnosisResponse(
        probable_cause=result.probable_cause,
        confidence=result.confidence,
        similar_incidents=[vars(m) for m in result.similar_incidents],
        recommended_fixes=result.recommended_fixes,
        evidence=result.evidence,
    )


@router.post("/impact")
async def impact_analysis(component: str, user=Depends(get_current_user)):
    from app.services.knowledge_graph.service import KnowledgeGraphService
    kg = KnowledgeGraphService()
    return await kg.get_impact_analysis(component)
