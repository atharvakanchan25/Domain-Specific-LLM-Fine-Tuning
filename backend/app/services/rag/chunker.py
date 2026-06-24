from __future__ import annotations
from dataclasses import dataclass
import re


@dataclass
class Chunk:
    text: str
    index: int
    token_count: int
    metadata: dict


class Chunker:
    def __init__(self, chunk_size: int = 512, overlap: int = 64):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        tokens = text.split()  # simple whitespace split; swap for tiktoken if needed
        chunks, i, idx = [], 0, 0
        while i < len(tokens):
            window = tokens[i: i + self.chunk_size]
            chunks.append(Chunk(
                text=" ".join(window),
                index=idx,
                token_count=len(window),
                metadata=metadata or {},
            ))
            i += self.chunk_size - self.overlap
            idx += 1
        return chunks
