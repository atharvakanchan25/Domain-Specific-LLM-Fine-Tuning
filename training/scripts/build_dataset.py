#!/usr/bin/env python
"""
training/scripts/build_dataset.py
Drives the DatasetBuilder against a local corpus directory.
Usage: python build_dataset.py --corpus /path/to/corpus --output training/data/splits
"""
import sys
import asyncio
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from training.dataset_builder.builder import DatasetBuilder


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus",  required=True, help="Directory of parsed text files")
    parser.add_argument("--output",  default="training/data/splits")
    parser.add_argument("--incidents", help="JSON file of incidents (optional)")
    args = parser.parse_args()

    builder = DatasetBuilder(Path(args.output))
    corpus_dir = Path(args.corpus)

    code_chunks = [
        {"content": f.read_text(errors="ignore"), "source_path": str(f)}
        for f in corpus_dir.rglob("*.py")
    ] + [
        {"content": f.read_text(errors="ignore"), "source_path": str(f)}
        for f in corpus_dir.rglob("*.md")
    ]

    examples = builder.from_code_files(code_chunks)

    if args.incidents:
        import json
        incidents = json.loads(Path(args.incidents).read_text())
        examples += builder.from_incidents(incidents)

    clean = builder.validate_and_filter(examples)
    counts = builder.split_and_save(clean)
    print(f"Dataset built: {counts}")


if __name__ == "__main__":
    main()
