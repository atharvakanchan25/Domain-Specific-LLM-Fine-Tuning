from __future__ import annotations
from functools import lru_cache
from sentence_transformers import SentenceTransformer
from app.core.config import settings
import numpy as np


@lru_cache(maxsize=1)
def _load_model() -> SentenceTransformer:
    return SentenceTransformer(settings.EMBEDDING_MODEL)


class Embedder:
    def __init__(self):
        self.model = _load_model()

    async def embed(self, text: str) -> list[float]:
        return self.model.encode(text, normalize_embeddings=True).tolist()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        vecs = self.model.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
        return vecs.tolist()
