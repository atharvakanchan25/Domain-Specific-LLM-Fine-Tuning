"""
Module 3: Dataset Builder
Generates instruction-tuning datasets from code, docs, bugs, commits.
"""
from __future__ import annotations
import json
import logging
import random
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class TrainingExample:
    instruction: str
    input: str
    output: str
    source: str
    quality_score: float = 1.0


PROMPT_TEMPLATES = {
    "explain_code": "Explain what the following code does and its business purpose:\n{code}",
    "explain_function": "What does this function do? Explain in plain English:\n{code}",
    "root_cause": "Analyze this incident and identify the root cause:\n{incident}",
    "arch_question": "Explain the architectural decision behind:\n{context}",
    "bug_fix": "The following code has a bug. Identify and fix it:\n{code}",
    "onboarding": "Generate onboarding documentation for a new developer joining the {service} team.",
    "migration": "Create a migration plan for {description}.",
    "dependency": "List all dependencies and impact of changing {component}.",
}


class DatasetBuilder:

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def from_code_files(self, code_chunks: list[dict]) -> list[TrainingExample]:
        try:
            from training.dataset_builder.sources.code_source import (
                extract_python_units, extract_generic_units, code_units_to_examples, LANG_MAP,
            )
        except ImportError:
            from sources.code_source import (  # type: ignore
                extract_python_units, extract_generic_units, code_units_to_examples, LANG_MAP,
            )
        examples = []
        for chunk in code_chunks:
            source_path = chunk.get("source_path", "")
            suffix = Path(source_path).suffix.lower()
            language = LANG_MAP.get(suffix)
            if language == "python":
                units = extract_python_units(Path(source_path))
            elif language:
                units = extract_generic_units(Path(source_path), language)
            else:
                # Fallback: treat whole chunk as a single explain_code example
                content = chunk.get("content", "")
                if len(content) > 50:
                    examples.append(TrainingExample(
                        instruction=PROMPT_TEMPLATES["explain_code"].format(code=content[:1500]),
                        input="",
                        output=f"This file ({Path(source_path).name}) contains code or documentation.",
                        source=source_path,
                    ))
                continue
            for ex in code_units_to_examples(units):
                examples.append(TrainingExample(
                    instruction=ex["instruction"],
                    input=ex["input"],
                    output=ex["output"],
                    source=ex["source"],
                ))
        return examples

    def from_incidents(self, incidents: list[dict]) -> list[TrainingExample]:
        examples = []
        for inc in incidents:
            if not inc.get("root_cause"):
                continue
            examples.append(TrainingExample(
                instruction=PROMPT_TEMPLATES["root_cause"].format(
                    incident=f"{inc['title']}\n{inc['description']}"
                ),
                input="",
                output=f"Root Cause: {inc['root_cause']}\nResolution: {inc.get('resolution', 'N/A')}",
                source="incident",
            ))
        return examples

    def from_arch_decisions(self, decisions: list[dict]) -> list[TrainingExample]:
        examples = []
        for d in decisions:
            examples.append(TrainingExample(
                instruction=PROMPT_TEMPLATES["arch_question"].format(context=d["title"]),
                input=d.get("context", ""),
                output=f"{d['decision']}\n\nRationale: {d['rationale']}",
                source="arch_decision",
            ))
        return examples

    def validate_and_filter(self, examples: list[TrainingExample]) -> list[TrainingExample]:
        seen, clean = set(), []
        for ex in examples:
            key = ex.instruction[:100]
            if key in seen:
                continue
            if len(ex.output) < 20 or "PLACEHOLDER" in ex.output:
                continue
            seen.add(key)
            clean.append(ex)
        return clean

    def split_and_save(self, examples: list[TrainingExample],
                        train_ratio=0.8, val_ratio=0.1) -> dict:
        random.shuffle(examples)
        n = len(examples)
        train_end = int(n * train_ratio)
        val_end = train_end + int(n * val_ratio)
        splits = {
            "train": examples[:train_end],
            "validation": examples[train_end:val_end],
            "test": examples[val_end:],
        }
        for split_name, split_data in splits.items():
            path = self.output_dir / f"{split_name}.jsonl"
            with open(path, "w") as f:
                for ex in split_data:
                    f.write(json.dumps(asdict(ex)) + "\n")
            logger.info("split_saved", split=split_name, count=len(split_data))
        return {k: len(v) for k, v in splits.items()}
