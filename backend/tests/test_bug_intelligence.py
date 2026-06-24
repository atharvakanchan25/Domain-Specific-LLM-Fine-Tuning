import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.bug_intelligence.engine import BugIntelligenceEngine, BugMatch


@pytest.fixture
def engine():
    embedder = AsyncMock()
    embedder.embed.return_value = [0.1] * 1024
    vector_store = AsyncMock()
    vector_store.search.return_value = [
        MagicMock(
            id="inc-1",
            score=0.91,
            payload={
                "title": "DB connection timeout",
                "root_cause": "Connection pool exhaustion",
                "resolution": "Increase pool size to 50",
            },
        ),
        MagicMock(
            id="inc-2",
            score=0.85,
            payload={
                "title": "Payment service timeout",
                "root_cause": "Connection pool exhaustion",
                "resolution": "Optimise long-running queries",
            },
        ),
    ]
    return BugIntelligenceEngine(embedder, vector_store, None)


@pytest.mark.asyncio
async def test_diagnose_returns_result(engine):
    result = await engine.diagnose("Database timeout in payment service")
    assert result.probable_cause == "Connection pool exhaustion"
    assert result.confidence > 0.5
    assert len(result.similar_incidents) == 2
    assert len(result.recommended_fixes) > 0


@pytest.mark.asyncio
async def test_diagnose_no_matches():
    embedder = AsyncMock()
    embedder.embed.return_value = [0.0] * 1024
    vs = AsyncMock()
    vs.search.return_value = []
    engine = BugIntelligenceEngine(embedder, vs, None)
    result = await engine.diagnose("unknown error xyz")
    assert result.confidence == 0.0
    assert result.similar_incidents == []
