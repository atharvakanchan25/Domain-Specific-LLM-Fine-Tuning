from app.services.agents.llm_client import generate, SYSTEM_PROMPT
from app.services.org_memory.engine import OrgMemoryEngine


class OrgMemoryAgent:
    def __init__(self, memory: OrgMemoryEngine):
        self.memory = memory

    async def run(self, query: str) -> dict:
        memories = await self.memory.query(query, top_k=5)
        context = "\n\n".join(
            f"Decision: {m.get('title','')}\n"
            f"Rationale: {m.get('rationale','')}\n"
            f"Alternatives: {m.get('alternatives_considered', {})}"
            for m in memories
        )
        answer = await generate(
            system_prompt=SYSTEM_PROMPT,
            user_message=f"Organisational memory:\n{context}\n\nQuestion: {query}",
        )
        return {"agent": "org_memory", "answer": answer, "memories": memories}
