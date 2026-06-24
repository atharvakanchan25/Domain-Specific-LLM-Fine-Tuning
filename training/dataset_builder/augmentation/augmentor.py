"""
training/dataset_builder/augmentation/augmentor.py
Generates additional training examples via:
1. Question paraphrasing (rule-based + LLM-assisted)
2. Multi-turn conversation synthesis
3. Negative examples (incorrect answers the model should refuse/correct)
"""
from __future__ import annotations
import random
import re


# ── Rule-based paraphrase templates ───────────────────────────────────────────
_PARAPHRASE_MAP: list[tuple[re.Pattern, list[str]]] = [
    (re.compile(r"^Explain (.+)$", re.I), [
        "Can you describe {0}?",
        "What is {0}?",
        "Provide an explanation of {0}.",
        "Give me an overview of {0}.",
    ]),
    (re.compile(r"^What does (.+) do\??$", re.I), [
        "Describe the purpose of {0}.",
        "How does {0} work?",
        "Explain the functionality of {0}.",
    ]),
    (re.compile(r"^Why was (.+) (chosen|selected|decided)\??$", re.I), [
        "What motivated the choice of {0}?",
        "What is the rationale behind selecting {0}?",
        "Explain the reasons for choosing {0}.",
    ]),
    (re.compile(r"^How (?:was|is) (.+) (implemented|built|designed)\??$", re.I), [
        "Describe the implementation of {0}.",
        "Walk me through how {0} works.",
        "What is the design of {0}?",
    ]),
    (re.compile(r"^Analyze (.+)$", re.I), [
        "Perform a root cause analysis of {0}.",
        "Investigate {0} and identify the cause.",
        "What caused {0}?",
    ]),
]


def paraphrase_instruction(instruction: str) -> list[str]:
    """Return up to 3 paraphrased versions of an instruction."""
    variants = []
    for pattern, templates in _PARAPHRASE_MAP:
        m = pattern.match(instruction)
        if m:
            subject = m.group(1)
            chosen = random.sample(templates, min(3, len(templates)))
            for t in chosen:
                variants.append(t.format(subject))
            break
    return variants


def augment_with_paraphrases(
    examples: list[dict],
    max_per_example: int = 2,
    augment_fraction: float = 0.4,
) -> list[dict]:
    """
    For a random fraction of examples, add paraphrased-instruction variants.
    Keeps the same input/output, only changes the instruction wording.
    """
    augmented = []
    pool = [e for e in examples if random.random() < augment_fraction]
    for ex in pool:
        variants = paraphrase_instruction(ex["instruction"])
        for v in variants[:max_per_example]:
            augmented.append({
                **ex,
                "instruction": v,
                "source": ex.get("source", "") + ":paraphrase",
            })
    return augmented


def build_multi_turn(examples: list[dict], pairs: int = 200) -> list[dict]:
    """
    Combine two related examples into a multi-turn conversation format.
    Useful for teaching the model to maintain context across turns.
    """
    by_category: dict[str, list[dict]] = {}
    for ex in examples:
        cat = ex.get("category", "general")
        by_category.setdefault(cat, []).append(ex)

    multi_turn = []
    for _ in range(pairs):
        cat = random.choice(list(by_category.keys()))
        pool = by_category[cat]
        if len(pool) < 2:
            continue
        turn1, turn2 = random.sample(pool, 2)
        conversation = (
            f"<|start_header_id|>user<|end_header_id|>\n{turn1['instruction']}\n"
            f"{turn1.get('input','')}<|eot_id|>"
            f"<|start_header_id|>assistant<|end_header_id|>\n{turn1['output']}<|eot_id|>"
            f"<|start_header_id|>user<|end_header_id|>\n{turn2['instruction']}\n"
            f"{turn2.get('input','')}<|eot_id|>"
            f"<|start_header_id|>assistant<|end_header_id|>\n{turn2['output']}<|eot_id|>"
        )
        multi_turn.append({
            "instruction": "[MULTI_TURN]",
            "input": "",
            "output": conversation,
            "source": f"multi_turn:{cat}",
            "category": cat,
            "quality_score": 0.8,
        })
    return multi_turn


def augment_all(examples: list[dict]) -> list[dict]:
    paraphrases = augment_with_paraphrases(examples)
    multi = build_multi_turn(examples)
    return examples + paraphrases + multi
