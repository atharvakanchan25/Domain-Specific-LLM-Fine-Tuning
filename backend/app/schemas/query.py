from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    conversation_id: str | None = None
    mode: str = "hybrid"
    entity_hint: str | None = None


class Citation(BaseModel):
    chunk_id: str
    source: str
    score: float
    excerpt: str


class GraphNode(BaseModel):
    name: str
    type: str
    rel: str | None = None


class QueryResponse(BaseModel):
    answer: str
    conversation_id: str
    plan: str | None = None
    agent_outputs: list[dict] = []
    citations: list[Citation] = []
    graph_context: list[GraphNode] = []
    confidence: float = 0.0


class DiagnosisRequest(BaseModel):
    error_description: str
    service: str | None = None


class BugMatch(BaseModel):
    incident_id: str
    title: str
    similarity: float
    root_cause: str
    resolution: str


class DiagnosisResponse(BaseModel):
    probable_cause: str
    confidence: float
    similar_incidents: list[BugMatch]
    recommended_fixes: list[str]
    evidence: list[str]
