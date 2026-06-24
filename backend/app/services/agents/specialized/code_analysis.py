from app.services.agents.llm_client import generate, SYSTEM_PROMPT
from app.services.rag.query import RAGQueryService


class CodeAnalysisAgent:
    def __init__(self, rag: RAGQueryService):
        self.rag = rag

    async def run(self, query: str) -> dict:
        results = await self.rag.retrieve(query, top_k=6)
        context = "\n\n".join(r["content"] for r in results)
        answer = await generate(
            system_prompt=SYSTEM_PROMPT,
            user_message=f"Context:\n{context}\n\nQuestion: {query}",
        )
        return {
            "agent": "code_analysis",
            "answer": answer,
            "citations": [{"chunk_id": r["id"], "source": r["metadata"].get("source_path", ""),
                           "score": r["score"], "excerpt": r["content"][:200]} for r in results],
        }
