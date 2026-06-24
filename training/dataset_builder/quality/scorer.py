"""
training/dataset_builder/quality/scorer.py
Scores and filters training examples for quality.
Criteria: length, lexical diversity, output completeness, no placeholders.
"""
from __future__ import annotations
import re
from dataclasses import dataclass


_PLACEHOLDER = re.compile(
    r"\[placeholder|TODO|fill with|to be completed|not implemented\]",
    re.IGNORECASE,
)
_BOILERPLATE = re.compile(
    r"^(pass|return|raise NotImplementedError|\.\.\.)\s*$",
    re.MULTILINE,
)


@dataclass
class QualityScore:
    length_score: float        # 0-1, based on output word count
    diversity_score: float     # 0-1, type-token ratio
    completeness_score: float  # 0-1, no placeholders / boilerplate
    total: float


def score(example: dict) -> QualityScore:
    output = example.get("output", "")
    instruction = example.get("instruction", "")
    words = output.split()
    word_count = len(words)

    # Length score: ideal range 30-500 words
    if word_count < 10:
        length_score = 0.0
    elif word_count < 30:
        length_score = word_count / 30
    elif word_count <= 500:
        length_score = 1.0
    else:
        length_score = max(0.5, 1.0 - (word_count - 500) / 2000)

    # Lexical diversity (type-token ratio) on output
    unique_words = len(set(w.lower() for w in words))
    ttr = unique_words / max(word_count, 1)
    diversity_score = min(1.0, ttr * 2)  # TTR > 0.5 → full score

    # Completeness: penalise placeholders and boilerplate
    has_placeholder = bool(_PLACEHOLDER.search(output))
    has_boilerplate = bool(_BOILERPLATE.search(output))
    has_short_instruction = len(instruction.split()) < 4
    completeness_score = 1.0
    if has_placeholder:
        completeness_score -= 0.8
    if has_boilerplate:
        completeness_score -= 0.5
    if has_short_instruction:
        completeness_score -= 0.2
    completeness_score = max(0.0, completeness_score)

    total = (length_score * 0.4 + diversity_score * 0.3 + completeness_score * 0.3)
    return QualityScore(
        length_score=round(length_score, 3),
        diversity_score=round(diversity_score, 3),
        completeness_score=round(completeness_score, 3),
        total=round(total, 3),
    )


def filter_examples(
    examples: list[dict],
    min_score: float = 0.45,
) -> list[dict]:
    filtered = []
    for ex in examples:
        s = score(ex)
        if s.total >= min_score:
            ex["quality_score"] = s.total
            filtered.append(ex)
    return filtered
