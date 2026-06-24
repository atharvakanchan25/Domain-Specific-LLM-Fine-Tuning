import pytest
from app.services.rag.chunker import Chunker


def test_basic_chunking():
    chunker = Chunker(chunk_size=10, overlap=2)
    text = " ".join(str(i) for i in range(50))
    chunks = chunker.chunk(text)
    assert len(chunks) > 1
    assert all(c.token_count <= 10 for c in chunks)


def test_overlap():
    chunker = Chunker(chunk_size=5, overlap=2)
    text = "a b c d e f g h i j"
    chunks = chunker.chunk(text)
    tokens_0 = set(chunks[0].text.split())
    tokens_1 = set(chunks[1].text.split())
    assert len(tokens_0 & tokens_1) == 2  # 2 token overlap


def test_short_text():
    chunker = Chunker(chunk_size=100, overlap=10)
    chunks = chunker.chunk("hello world")
    assert len(chunks) == 1
    assert chunks[0].text == "hello world"
