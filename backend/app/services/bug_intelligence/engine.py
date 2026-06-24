"""
Module 5: Historical Bug Intelligence Engine
Clusters past incidents, identifies root-cause patterns,
and scores new errors against historical evidence.
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from app.core.logging import logger


@dataclass
class BugMatch:
    incident_id: str
    title: str
    similarity: float
    root_cause: str
    resolution: str


@dataclass
class DiagnosisResult:
    probable_cause: str
    confidence: float
    similar_incidents: list[BugMatch]
    recommended_fixes: list[str]
    evidence: list[str]


class BugIntelligenceEngine:

    def __init__(self, embedder, vector_store, db_session):
        self.embedder = embedder
        self.vector_store = vector_store
        self.db = db_session

    async def diagnose(self, error_description: str, service: str | None = None) -> DiagnosisResult:
        """
        Main entry: embed the error, search for similar incidents,
        cluster root causes, return ranked diagnosis.
        """
        vector = await self.embedder.embed(error_description)
        similar = await self.vector_store.search(
            vector=vector,
            collection="incidents",
            top_k=10,
            filters={"service": service} if service else None,
        )
        if not similar:
            return DiagnosisResult(
                probable_cause="Unknown — no historical matches found.",
                confidence=0.0,
                similar_incidents=[],
                recommended_fixes=[],
                evidence=[],
            )
        matches = [
            BugMatch(
                incident_id=r.id,
                title=r.payload.get("title", ""),
                similarity=r.score,
                root_cause=r.payload.get("root_cause", ""),
                resolution=r.payload.get("resolution", ""),
            )
            for r in similar
        ]
        top_cause, confidence = self._cluster_root_causes([m.root_cause for m in matches],
                                                           [m.similarity for m in matches])
        fixes = self._extract_fixes(matches)
        return DiagnosisResult(
            probable_cause=top_cause,
            confidence=round(confidence, 2),
            similar_incidents=matches[:5],
            recommended_fixes=fixes,
            evidence=[m.title for m in matches[:3]],
        )

    def _cluster_root_causes(self, causes: list[str], scores: list[float]) -> tuple[str, float]:
        if not causes:
            return "Unknown", 0.0
        weighted: dict[str, float] = {}
        for cause, score in zip(causes, scores):
            weighted[cause] = weighted.get(cause, 0.0) + score
        best = max(weighted, key=weighted.__getitem__)
        total = sum(weighted.values())
        confidence = weighted[best] / total if total else 0.0
        return best, confidence

    def _extract_fixes(self, matches: list[BugMatch]) -> list[str]:
        seen, fixes = set(), []
        for m in matches:
            if m.resolution and m.resolution not in seen:
                fixes.append(m.resolution)
                seen.add(m.resolution)
        return fixes[:5]

    async def index_incident(self, incident: dict) -> None:
        """Embed and store a new incident for future matching."""
        text = f"{incident.get('title', '')} {incident.get('description', '')} {incident.get('root_cause', '')}"
        vector = await self.embedder.embed(text)
        await self.vector_store.upsert_single(
            id=incident["id"],
            vector=vector,
            payload=incident,
            collection="incidents",
        )
        logger.info("incident_indexed", id=incident["id"])
