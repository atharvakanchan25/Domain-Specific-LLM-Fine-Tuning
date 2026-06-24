from app.services.agents.llm_client import generate, SYSTEM_PROMPT
from app.services.bug_intelligence.engine import BugIntelligenceEngine


class BugDiagnosisAgent:
    def __init__(self, bug_engine: BugIntelligenceEngine):
        self.bug_engine = bug_engine

    async def run(self, query: str, service: str | None = None) -> dict:
        diagnosis = await self.bug_engine.diagnose(query, service)
        evidence_text = "\n".join(
            f"- {m.title} (similarity: {m.similarity:.2f}): {m.root_cause}"
            for m in diagnosis.similar_incidents
        )
        answer = await generate(
            system_prompt=SYSTEM_PROMPT,
            user_message=(
                f"Historical evidence:\n{evidence_text}\n\n"
                f"Probable cause: {diagnosis.probable_cause} "
                f"(confidence: {diagnosis.confidence:.0%})\n\n"
                f"Question: {query}\n\n"
                "Provide a detailed diagnosis and recommended fixes."
            ),
        )
        return {
            "agent": "bug_diagnosis",
            "answer": answer,
            "diagnosis": {
                "probable_cause": diagnosis.probable_cause,
                "confidence": diagnosis.confidence,
                "recommended_fixes": diagnosis.recommended_fixes,
            },
        }
