"""
training/dataset_builder/quality/deduplicator.py
Near-duplicate removal using MinHash LSH.
Falls back to exact-hash dedup if datasketch is not installed.
"""
from __future__ import annotations
import hashlib
import re


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _shingles(text: str, k: int = 5) -> set[str]:
    tokens = text.split()
    return {" ".join(tokens[i: i + k]) for i in range(len(tokens) - k + 1)}


def deduplicate(examples: list[dict], threshold: float = 0.85) -> list[dict]:
    """
    Remove near-duplicates based on instruction+output jaccard similarity.
    Uses MinHash when datasketch is available, otherwise exact SHA-256.
    """
    try:
        from datasketch import MinHash, MinHashLSH
        return _minhash_dedup(examples, threshold)
    except ImportError:
        return _exact_dedup(examples)


def _exact_dedup(examples: list[dict]) -> list[dict]:
    seen: set[str] = set()
    clean: list[dict] = []
    for ex in examples:
        key = hashlib.sha256(
            (_normalise(ex.get("instruction", "")) + _normalise(ex.get("output", ""))).encode()
        ).hexdigest()
        if key not in seen:
            seen.add(key)
            clean.append(ex)
    return clean


def _minhash_dedup(examples: list[dict], threshold: float) -> list[dict]:
    from datasketch import MinHash, MinHashLSH

    lsh = MinHashLSH(threshold=threshold, num_perm=128)
    clean: list[dict] = []

    for i, ex in enumerate(examples):
        text = _normalise(ex.get("instruction", "") + " " + ex.get("output", ""))
        mh = MinHash(num_perm=128)
        for shingle in _shingles(text):
            mh.update(shingle.encode("utf-8"))
        key = f"ex_{i}"
        try:
            if not lsh.query(mh):
                lsh.insert(key, mh)
                clean.append(ex)
        except ValueError:
            # key already exists — skip
            pass
    return clean
