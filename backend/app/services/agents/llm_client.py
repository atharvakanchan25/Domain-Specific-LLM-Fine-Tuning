from __future__ import annotations
from openai import AsyncOpenAI
from app.core.config import settings


_client: AsyncOpenAI | None = None


def get_llm_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(base_url=settings.VLLM_BASE_URL, api_key="local")
    return _client


async def generate(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> str:
    client = get_llm_client()
    response = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content or ""


SYSTEM_PROMPT = """You are an expert AI senior software engineer with deep knowledge of this
organisation's codebase, architecture, and history. Answer questions accurately using the
provided context. Always cite sources when available. If you are unsure, say so."""
