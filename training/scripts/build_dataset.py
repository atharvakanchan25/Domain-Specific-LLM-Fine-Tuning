#!/usr/bin/env python
"""
training/scripts/build_dataset.py
Drives the DatasetBuilder against a local corpus directory.
Usage: python build_dataset.py --corpus /path/to/corpus --output training/data/splits
"""
import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from training.dataset_builder.builder import DatasetBuilder
from training.dataset_builder.sources.code_source import (
    extract_python_units, extract_generic_units,
    code_units_to_examples, LANG_MAP,
)
from training.dataset_builder.sources.incident_source import incidents_to_examples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus",    required=True, help="Directory of source files")
    parser.add_argument("--output",    default="training/data/splits")
    parser.add_argument("--incidents", help="JSON file of incidents (optional)")
    parser.add_argument("--logs",      help="Directory of log files (optional)")
    args = parser.parse_args()

    builder = DatasetBuilder(Path(args.output))
    corpus_dir = Path(args.corpus)

    # Build code_chunks list for the builder (used for non-Python fallback)
    code_chunks = [
        {"content": f.read_text(errors="ignore"), "source_path": str(f)}
        for ext in ("*.py", "*.js", "*.ts", "*.java", "*.go", "*.md")
        for f in corpus_dir.rglob(ext)
    ]

    examples = builder.from_code_files(code_chunks)

    if args.incidents:
        incidents = json.loads(Path(args.incidents).read_text())
        examples += builder.from_incidents(incidents)
        # Also use the richer incident source
        examples_raw = incidents_to_examples(incidents)
        from training.dataset_builder.builder import TrainingExample
        for ex in examples_raw:
            examples.append(TrainingExample(
                instruction=ex["instruction"],
                input=ex["input"],
                output=ex["output"],
                source=ex["source"],
            ))

    if args.logs:
        from training.dataset_builder.sources.incident_source import extract_from_logs
        from training.dataset_builder.builder import TrainingExample
        for log_file in Path(args.logs).rglob("*.log"):
            log_text = log_file.read_text(errors="ignore")
            for ex in extract_from_logs(log_text, service=log_file.stem):
                examples.append(TrainingExample(
                    instruction=ex["instruction"],
                    input=ex["input"],
                    output=ex["output"],
                    source=ex["source"],
                ))

    clean = builder.validate_and_filter(examples)
    counts = builder.split_and_save(clean)
    print(f"Dataset built: {counts}")


if __name__ == "__main__":
    main()
