from app.services.agents.llm_client import generate, SYSTEM_PROMPT
from app.services.knowledge_graph.service import KnowledgeGraphService
from app.services.rag.query import RAGQueryService


class ArchitectureAgent:
    def __init__(self, rag: RAGQueryService, kg: KnowledgeGraphService):
        self.rag = rag
        self.kg = kg

    async def run(self, query: str, entity_hint: str | None = None) -> dict:
        rag_result = await self.rag.retrieve_with_graph(query, entity_hint)
        graph_ctx = rag_result["graph_context"]
        rag_ctx = "\n\n".join(r["content"] for r in rag_result["chunks"])
        graph_text = "\n".join(f"{g['name']} -{g['rel']}-> {g.get('type','')}" for g in graph_ctx)
        answer = await generate(
            system_prompt=SYSTEM_PROMPT,
            user_message=f"RAG Context:\n{rag_ctx}\n\nGraph Context:\n{graph_text}\n\nQuestion: {query}",
        )
        return {
            "agent": "architecture",
            "answer": answer,
            "graph_context": graph_ctx,
        }
